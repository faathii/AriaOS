use crate::manifest::{find_tool, RegisteredConnector};
use crate::ollama::{initial_history, run_agent_turn, OllamaClient};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};

#[cfg(unix)]
pub fn serve_socket(connectors: Vec<RegisteredConnector>, model: Option<String>) -> Result<(), String> {
    use std::fs;
    use std::io::{BufRead, BufReader, Write};
    use std::os::unix::fs::PermissionsExt;
    use std::os::unix::net::UnixListener;

    let socket_path = resolve_socket_path();
    if socket_path.exists() {
        let _ = fs::remove_file(&socket_path);
    }
    if let Some(parent) = socket_path.parent() {
        let _ = fs::create_dir_all(parent);
    }

    let listener = UnixListener::bind(&socket_path)
        .map_err(|e| format!("Failed to bind {}: {e}", socket_path.display()))?;
    let _ = fs::set_permissions(&socket_path, fs::Permissions::from_mode(0o666));
    println!("aria-daemon listening on {}", socket_path.display());

    for stream in listener.incoming() {
        let Ok(mut stream) = stream else { continue };
        let mut reader = BufReader::new(stream.try_clone().map_err(|e| e.to_string())?);
        let mut line = String::new();
        if reader.read_line(&mut line).is_err() || line.trim().is_empty() {
            continue;
        }
        let response = handle_ipc_request(line.trim(), &connectors, model.clone());
        let _ = writeln!(stream, "{response}");
    }
    Ok(())
}

#[cfg(not(unix))]
pub fn serve_socket(_connectors: Vec<RegisteredConnector>, _model: Option<String>) -> Result<(), String> {
    Err("Unix socket server mode is only supported on Linux/Unix".to_string())
}

#[cfg(unix)]
fn resolve_socket_path() -> std::path::PathBuf {
    if let Ok(custom) = std::env::var("ARIAOS_SOCKET_PATH") {
        return std::path::PathBuf::from(custom);
    }
    let runtime_dir = std::path::PathBuf::from("/run/ariaos");
    if runtime_dir.exists() {
        runtime_dir.join("agent.sock")
    } else {
        std::path::PathBuf::from("/tmp/ariaos-agent.sock")
    }
}

fn handle_ipc_request(
    raw: &str,
    connectors: &[RegisteredConnector],
    model: Option<String>,
) -> Value {
    let Ok(req) = serde_json::from_str::<Value>(raw) else {
        return json!({"ok": false, "error": "Invalid JSON request"});
    };

    match req.get("action").and_then(|v| v.as_str()) {
        Some("list_tools") => {
            let list: Vec<Value> = connectors
                .iter()
                .map(|c| {
                    json!({
                        "id": c.manifest.id,
                        "name": c.manifest.name,
                        "transport": c.manifest.transport,
                        "tools": c.manifest.tools
                    })
                })
                .collect();
            json!({"ok": true, "connectors": list})
        }
        Some("call") => {
            let conn_id = req.get("connector").and_then(|v| v.as_str()).unwrap_or("");
            let tool = req.get("tool").and_then(|v| v.as_str()).unwrap_or("");
            let args = req.get("arguments").cloned().unwrap_or_else(|| json!({}));
            let approved = req.get("approved").and_then(|v| v.as_bool()).unwrap_or(false);

            let Some((conn, spec)) = find_tool(connectors, conn_id, tool) else {
                return json!({"ok": false, "error": "Unknown connector or tool"});
            };
            let is_allowed = approved || check_approval(conn_id, tool, spec.risk_level, &args, ApprovalMode::ReadOnly);
            if !is_allowed {
                audit_log(conn_id, tool, spec.risk_level, "confirmation_required", &args);
                return json!({
                    "ok": false,
                    "error": "Tool requires interactive confirmation",
                    "requires_confirmation": true,
                    "risk_level": spec.risk_level.as_str()
                });
            }
            match call_stdio_tool(conn, tool, args.clone()) {
                Ok(data) => {
                    audit_log(conn_id, tool, spec.risk_level, "ok", &args);
                    json!({"ok": true, "result": data})
                }
                Err(err) => {
                    audit_log(conn_id, tool, spec.risk_level, "error", &args);
                    json!({"ok": false, "error": err})
                }
            }
        }
        Some("ask") => {
            let prompt = req.get("prompt").and_then(|v| v.as_str()).unwrap_or("");
            if prompt.is_empty() {
                return json!({"ok": false, "error": "Missing 'prompt'"});
            }
            let client = OllamaClient::from_env(model);
            let mut history = initial_history();
            match run_agent_turn(&client, connectors, &mut history, prompt, ApprovalMode::ReadOnly) {
                Ok(answer) => json!({"ok": true, "answer": answer}),
                Err(err) => json!({"ok": false, "error": err}),
            }
        }
        _ => json!({"ok": false, "error": "Unsupported action (use list_tools, call, or ask)"}),
    }
}

