use crate::manifest::{
    find_tool, ollama_tools_payload, parse_qualified_tool_name, RegisteredConnector,
};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};
use std::env;
use std::time::Duration;

const SYSTEM_PROMPT: &str = "\
You ARE Aria, the OS itself inside AriaOS (Arch Linux kernel + systemd + KDE Plasma 6). \
You operate natively across every layer of the computer:
- Kernel & Hardware: os-kernel (telemetry, dmesg, PCI/USB, sysctl, kernel modules), os-storage (disks/archives)
- Core System & Security: os-system (systemd/processes), os-packages (pacman), security-antivirus (ClamAV + quarantine), security-vault-crypto, security-net-audit
- File Manager & Desktop Apps: os-files (Dolphin, search, XDG Trash, duplicates, organize), os-desktop, office, media, creative, dev & gaming connectors
Rules:\n\
1. Call all read-only tools (risk=read) you need immediately—even multiple tools in sequence—without asking first; aria-daemon enforces confirmation prompts for write and privileged tools.\n\
2. Never guess or fabricate system metrics, kernel state, malware scan outputs, or file counts. Always call the appropriate tool first.\n\
3. When organizing files, prefer dry-run (apply=false) first unless the user explicitly asks to apply changes.\n\
4. Respond concisely in the user's language based strictly on observed tool results.";

#[derive(Debug, Clone)]
pub enum AgentTurnOutcome {
    Answered(String),
    NeedsConfirmation {
        connector: String,
        tool: String,
        risk_level: String,
        arguments: Value,
    },
}

pub struct OllamaClient {
    pub base_url: String,
    pub model: String,
    agent: ureq::Agent,
}

impl OllamaClient {
    pub fn from_env(model_override: Option<String>) -> Self {
        let base_url = env::var("ARIAOS_OLLAMA_URL")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        let model = model_override
            .or_else(|| env::var("ARIAOS_MODEL").ok())
            .unwrap_or_else(|| "qwen2.5:3b".to_string());
        let agent = ureq::AgentBuilder::new()
            .timeout_connect(Duration::from_secs(5))
            .timeout_read(Duration::from_secs(180))
            .build();
        Self {
            base_url,
            model,
            agent,
        }
    }

    pub fn chat(&self, messages: &[Value], tools: &[Value]) -> Result<Value, String> {
        let url = format!("{}/api/chat", self.base_url.trim_end_matches('/'));
        let payload = json!({
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": false,
            "options": {
                "num_ctx": 8192
            }
        });

        let response = self
            .agent
            .post(&url)
            .send_json(payload)
            .map_err(|e| format!("Ollama request failed ({url}): {e}"))?;

        response
            .into_json::<Value>()
            .map_err(|e| format!("Invalid JSON from Ollama: {e}"))
    }
}

pub fn initial_history() -> Vec<Value> {
    vec![json!({
        "role": "system",
        "content": SYSTEM_PROMPT
    })]
}

pub fn run_agent_turn(
    client: &OllamaClient,
    connectors: &[RegisteredConnector],
    history: &mut Vec<Value>,
    user_prompt: &str,
    mode: ApprovalMode,
) -> Result<String, String> {
    match run_agent_turn_with_approvals(client, connectors, history, user_prompt, mode, &[])? {
        AgentTurnOutcome::Answered(text) => Ok(text),
        AgentTurnOutcome::NeedsConfirmation {
            connector,
            tool,
            risk_level,
            ..
        } => Ok(format!(
            "Confirmation required ({risk_level}) for {connector}.{tool}."
        )),
    }
}

pub fn run_agent_turn_with_approvals(
    client: &OllamaClient,
    connectors: &[RegisteredConnector],
    history: &mut Vec<Value>,
    user_prompt: &str,
    mode: ApprovalMode,
    approved_tools: &[String],
) -> Result<AgentTurnOutcome, String> {
    history.push(json!({
        "role": "user",
        "content": user_prompt
    }));

    let tools = ollama_tools_payload(connectors);
    let max_iterations = 8;

    for _ in 0..max_iterations {
        let reply = client.chat(history, &tools)?;
        let message = reply
            .get("message")
            .cloned()
            .ok_or_else(|| format!("Ollama response missing 'message': {reply}"))?;

        history.push(message.clone());

        let tool_calls = message
            .get("tool_calls")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        if tool_calls.is_empty() {
            let content = message
                .get("content")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            return Ok(AgentTurnOutcome::Answered(content));
        }

        for call in tool_calls {
            let func = call.get("function").cloned().unwrap_or(Value::Null);
            let qualified = func.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let args = func
                .get("arguments")
                .cloned()
                .unwrap_or_else(|| json!({}));

            match execute_tool_call(connectors, qualified, args, mode, approved_tools) {
                Ok(tool_output) => {
                    history.push(json!({
                        "role": "tool",
                        "content": tool_output.to_string()
                    }));
                }
                Err(pending) => return Ok(pending),
            }
        }
    }

    Err("Reached maximum tool-calling iterations without a final answer".to_string())
}

fn execute_tool_call(
    connectors: &[RegisteredConnector],
    qualified_name: &str,
    args: Value,
    mode: ApprovalMode,
    approved_tools: &[String],
) -> Result<Value, AgentTurnOutcome> {
    let Some((connector_id, tool_name)) = parse_qualified_tool_name(qualified_name) else {
        return Ok(json!({"ok": false, "error": format!("Invalid tool identifier: {qualified_name}")}));
    };

    let Some((conn, spec)) = find_tool(connectors, connector_id, tool_name) else {
        return Ok(json!({"ok": false, "error": format!("Unknown tool: {qualified_name}")}));
    };

    eprintln!("[aria-daemon] -> calling {connector_id}.{tool_name} args={args}");

    let dot_name = format!("{connector_id}.{tool_name}");
    let explicitly_approved = approved_tools
        .iter()
        .any(|t| t == qualified_name || t == &dot_name);

    if !explicitly_approved && !check_approval(connector_id, tool_name, spec.risk_level, &args, mode) {
        if mode == ApprovalMode::ReadOnly {
            audit_log(connector_id, tool_name, spec.risk_level, "confirmation_required", &args);
            return Err(AgentTurnOutcome::NeedsConfirmation {
                connector: connector_id.to_string(),
                tool: tool_name.to_string(),
                risk_level: spec.risk_level.as_str().to_string(),
                arguments: args,
            });
        }
        audit_log(connector_id, tool_name, spec.risk_level, "denied", &args);
        return Ok(json!({
            "ok": false,
            "error": "Execution denied by user/policy"
        }));
    }

    match call_stdio_tool(conn, tool_name, args.clone()) {
        Ok(result) => {
            audit_log(connector_id, tool_name, spec.risk_level, "ok", &args);
            Ok(result)
        }
        Err(err) => {
            audit_log(connector_id, tool_name, spec.risk_level, "error", &args);
            Ok(json!({"ok": false, "error": err}))
        }
    }
}

