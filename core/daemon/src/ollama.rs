use crate::manifest::{
    find_tool, ollama_tools_payload, parse_qualified_tool_name, RegisteredConnector,
};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};
use std::env;
use std::time::Duration;

const SYSTEM_PROMPT: &str = "\
You are Aria, the OS-native AI agent embedded inside AriaOS (Arch Linux + KDE Plasma). \
You control the computer through structured tools exposed by system and application connectors. \
Rules:\n\
1. Call all read-only tools (risk=read) you need immediately—even multiple tools in sequence—without asking the user for permission first; aria-daemon automatically enforces confirmation prompts for write and privileged tools.\n\
2. Never guess or fabricate system metrics, file counts, or tool outputs. Always call the appropriate tool first.\n\
3. When organizing files, prefer dry-run (apply=false) first unless the user explicitly asks to apply changes.\n\
4. Respond concisely in the user's language based strictly on observed tool results.";

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
            "stream": false
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
            return Ok(content);
        }

        for call in tool_calls {
            let func = call.get("function").cloned().unwrap_or(Value::Null);
            let qualified = func.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let args = func
                .get("arguments")
                .cloned()
                .unwrap_or_else(|| json!({}));

            let tool_output = execute_tool_call(connectors, qualified, args, mode);
            history.push(json!({
                "role": "tool",
                "content": tool_output.to_string()
            }));
        }
    }

    Err("Reached maximum tool-calling iterations without a final answer".to_string())
}

fn execute_tool_call(
    connectors: &[RegisteredConnector],
    qualified_name: &str,
    args: Value,
    mode: ApprovalMode,
) -> Value {
    let Some((connector_id, tool_name)) = parse_qualified_tool_name(qualified_name) else {
        return json!({"ok": false, "error": format!("Invalid tool identifier: {qualified_name}")});
    };

    let Some((conn, spec)) = find_tool(connectors, connector_id, tool_name) else {
        return json!({"ok": false, "error": format!("Unknown tool: {qualified_name}")});
    };

    eprintln!("[aria-daemon] -> calling {connector_id}.{tool_name} args={args}");

    if !check_approval(connector_id, tool_name, spec.risk_level, &args, mode) {
        audit_log(connector_id, tool_name, spec.risk_level, "denied", &args);
        return json!({
            "ok": false,
            "error": "Execution denied by user/policy"
        });
    }

    match call_stdio_tool(conn, tool_name, args.clone()) {
        Ok(result) => {
            audit_log(connector_id, tool_name, spec.risk_level, "ok", &args);
            result
        }
        Err(err) => {
            audit_log(connector_id, tool_name, spec.risk_level, "error", &args);
            json!({"ok": false, "error": err})
        }
    }
}

