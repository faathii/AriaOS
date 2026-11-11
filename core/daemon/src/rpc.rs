use crate::manifest::RegisteredConnector;
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

/// Execute one tool on a stdio JSON-RPC 2.0 connector.
pub fn call_stdio_tool(
    connector: &RegisteredConnector,
    tool_name: &str,
    arguments: Value,
) -> Result<Value, String> {
    if connector.manifest.transport != "stdio" {
        return Err(format!(
            "Connector '{}' uses transport '{}', which is not executable over stdio yet",
            connector.manifest.id, connector.manifest.transport
        ));
    }
    let Some((program, args)) = connector.manifest.entrypoint.split_first() else {
        return Err(format!(
            "Connector '{}' has no entrypoint configured",
            connector.manifest.id
        ));
    };

    let mut child = Command::new(program)
        .args(args)
        .current_dir(&connector.root_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to spawn '{}': {e}", connector.manifest.id))?;

    let request = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    });

    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or_else(|| "Failed to open connector stdin".to_string())?;
        let line = format!("{request}\n");
        stdin
            .write_all(line.as_bytes())
            .map_err(|e| format!("Failed writing RPC request: {e}"))?;
    }
    // Drop stdin so stdio loops exit cleanly after processing the batch.
    drop(child.stdin.take());

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Failed to open connector stdout".to_string())?;
    let mut reader = BufReader::new(stdout);
    let mut response_line = String::new();
    reader
        .read_line(&mut response_line)
        .map_err(|e| format!("Failed reading RPC response: {e}"))?;

    let output = child
        .wait_with_output()
        .map_err(|e| format!("Failed waiting for connector: {e}"))?;

    if response_line.trim().is_empty() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!(
            "Connector '{}' returned empty response (status={}): {}",
            connector.manifest.id,
            output.status,
            stderr.trim()
        ));
    }

    let parsed: Value = serde_json::from_str(response_line.trim())
        .map_err(|e| format!("Invalid JSON-RPC response from connector: {e}"))?;

    if let Some(err) = parsed.get("error") {
        return Err(format!("Connector error: {err}"));
    }

    parsed
        .get("result")
        .cloned()
        .ok_or_else(|| "JSON-RPC response missing 'result'".to_string())
}

