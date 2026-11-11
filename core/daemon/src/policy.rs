use crate::manifest::RiskLevel;
use serde_json::{json, Value};
use std::env;
use std::fs::OpenOptions;
use std::io::{self, Write};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApprovalMode {
    Interactive,
    AutoWrite,
    ReadOnly,
}

pub fn check_approval(
    connector_id: &str,
    tool_name: &str,
    risk: RiskLevel,
    args: &Value,
    mode: ApprovalMode,
) -> bool {
    match risk {
        RiskLevel::Read => true,
        RiskLevel::Write => match mode {
            ApprovalMode::AutoWrite => true,
            ApprovalMode::ReadOnly => false,
            ApprovalMode::Interactive => prompt_user(connector_id, tool_name, risk, args),
        },
        RiskLevel::Privileged => match mode {
            ApprovalMode::ReadOnly => false,
            ApprovalMode::Interactive | ApprovalMode::AutoWrite => {
                prompt_user(connector_id, tool_name, risk, args)
            }
        },
    }
}

fn prompt_user(connector_id: &str, tool_name: &str, risk: RiskLevel, args: &Value) -> bool {
    eprintln!(
        "\n[ariaOS Policy] Confirmation required ({}): {}.{}",
        risk.as_str(),
        connector_id,
        tool_name
    );
    eprintln!("  Arguments: {args}");
    eprint!("  Allow execution? [y/N]: ");
    let _ = io::stderr().flush();

    let mut input = String::new();
    if io::stdin().read_line(&mut input).is_err() {
        return false;
    }
    matches!(input.trim().to_ascii_lowercase().as_str(), "y" | "yes" | "s" | "si")
}

pub fn audit_log(connector_id: &str, tool_name: &str, risk: RiskLevel, status: &str, args: &Value) {
    let path = env::var("ARIAOS_AUDIT_LOG")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/tmp/ariaos-audit.jsonl"));

    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    let entry = json!({
        "ts": ts,
        "connector": connector_id,
        "tool": tool_name,
        "risk_level": risk.as_str(),
        "status": status,
        "arguments": args
    });

    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(file, "{entry}");
    }
}

