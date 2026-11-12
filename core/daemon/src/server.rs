use crate::manifest::{find_tool, RegisteredConnector};
use crate::ollama::{initial_history, run_agent_turn_with_approvals, AgentTurnOutcome, OllamaClient};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};

#[cfg(unix)]
pub fn serve_socket(connectors: Vec<RegisteredConnector>, model: Option<String>) -> Result<(), String> {
    use std::fs;
    use std::io::{BufRead, BufReader, Write};
    use std::os::unix::fs::PermissionsExt;
    use std::os::unix::net::UnixListener;
    use std::sync::Arc;
    use std::thread;

    // Start the background Autonomic Kernel Governor (ZRAM, I/O scheduler, CPU governor & PSI mitigation)
    crate::kernel::spawn_autonomic_kernel_governor();

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
    let hw = crate::kernel::KernelTelemetry::collect();
    println!(
        "aria-daemon listening on {} [profile={}, AVX2={}]",
        socket_path.display(),
        hw.hardware_tier.as_str(),
        hw.silicon.avx2
    );

    let shared_connectors: Arc<[RegisteredConnector]> = Arc::from(connectors);

    for stream in listener.incoming() {
        let Ok(mut stream) = stream else { continue };
        let conns = Arc::clone(&shared_connectors);
        let mdl = model.clone();
        thread::spawn(move || {
            let Ok(cloned) = stream.try_clone() else { return };
            let mut reader = BufReader::new(cloned);
            let mut line = String::new();
            if reader.read_line(&mut line).is_err() || line.trim().is_empty() {
                return;
            }
            let response = handle_ipc_request(line.trim(), &conns, mdl);
            let _ = writeln!(stream, "{response}");
        });
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
        Some("kernel_telemetry") => {
            let k = crate::kernel::KernelTelemetry::collect();
            json!({"ok": true, "telemetry": k.to_json()})
        }
        Some("optimize_kernel") => {
            crate::kernel::optimize_kernel_memory()
        }
        Some("memory_status") => {
            let mem = crate::memory::NeuralMemory::load();
            json!({"ok": true, "memory": mem.summary_json()})
        }
        Some("catalog") => {
            let apps = crate::memory::build_universal_app_catalog();
            json!({"ok": true, "apps": apps, "total": apps.len()})
        }
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
            let approved_tools: Vec<String> = req
                .get("approved_tools")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|x| x.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();
            let client = OllamaClient::from_env(model);
            let mut history = initial_history();
            match run_agent_turn_with_approvals(
                &client,
                connectors,
                &mut history,
                prompt,
                ApprovalMode::ReadOnly,
                &approved_tools,
            ) {
                Ok(AgentTurnOutcome::Answered(answer)) => json!({"ok": true, "answer": answer}),
                Ok(AgentTurnOutcome::NeedsConfirmation {
                    connector,
                    tool,
                    risk_level,
                    arguments,
                }) => json!({
                    "ok": false,
                    "error": "Tool requires interactive confirmation",
                    "requires_confirmation": true,
                    "risk_level": risk_level,
                    "pending_call": {
                        "connector": connector,
                        "tool": tool,
                        "arguments": arguments
                    }
                }),
                Err(err) => json!({"ok": false, "error": err}),
            }
        }
        _ => json!({"ok": false, "error": "Unsupported action (use list_tools, call, or ask)"}),
    }
}

