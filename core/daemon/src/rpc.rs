use crate::manifest::RegisteredConnector;
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

/// Execute one tool on a stdio JSON-RPC 2.0 connector (with zero-overhead native Rust kernel fast-paths).
pub fn call_stdio_tool(
    connector: &RegisteredConnector,
    tool_name: &str,
    arguments: Value,
) -> Result<Value, String> {
    // Zero-overhead native Rust Kernel fast-path (<0.1ms, bypasses Python subprocess spawning)
    match (connector.manifest.id.as_str(), tool_name) {
        ("os-kernel", "kernel_telemetry")
        | ("os-kernel", "summary")
        | ("os-kernel", "cpu_memory_pressure")
        | ("os-system", "system_health_summary")
        | ("os-system", "health") => {
            let k = crate::kernel::KernelTelemetry::collect();
            return Ok(k.to_json());
        }
        ("os-system", "list_top_processes") | ("os-system", "top_processes") => {
            let limit = arguments
                .get("limit")
                .and_then(|v| v.as_u64())
                .unwrap_or(10) as usize;
            return Ok(crate::kernel::native_top_processes(limit.clamp(1, 50)));
        }
        ("os-storage", "list_block_devices") | ("os-storage", "disk_usage") => {
            return Ok(crate::kernel::native_disk_usage());
        }
        _ => {}
    }

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

    let (tx, rx) = std::sync::mpsc::channel();
    let conn_id = connector.manifest.id.clone();
    std::thread::spawn(move || {
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        let res = reader.read_line(&mut line).map(|_| line);
        let _ = tx.send(res);
    });

    let timeout = std::time::Duration::from_secs(25);
    let response_line = match rx.recv_timeout(timeout) {
        Ok(Ok(line)) => line,
        Ok(Err(e)) => {
            let _ = child.kill();
            return Err(format!("Failed reading RPC response from '{conn_id}': {e}"));
        }
        Err(_) => {
            let _ = child.kill();
            return Err(format!(
                "Timeout (25s) waiting for connector '{conn_id}' tool '{tool_name}'"
            ));
        }
    };

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

