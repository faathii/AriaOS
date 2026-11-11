//! aria-daemon: OS-native AI broker for AriaOS.
//!
//! Responsibilities:
//! 1. Discover connector manifests from system and user connector directories.
//! 2. Expose the local Unix socket (`/run/ariaos/agent.sock`) and D-Bus service
//!    (`org.ariaos.Agent1`) to `ariaOS-Command-Bar` and system hooks.
//! 3. Route natural-language intents through local Ollama models and dispatch
//!    validated tool calls across Tier 1 (D-Bus), Tier 2 (connectors), and Tier 3 (UI).
//! 4. Enforce `risk_level` policies (`read`, `write`, `privileged`) before execution.

use serde::Deserialize;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RiskLevel {
    Read,
    Write,
    Privileged,
}

#[derive(Debug, Deserialize)]
pub struct ToolSpec {
    pub name: String,
    pub description: String,
    pub risk_level: RiskLevel,
}

#[derive(Debug, Deserialize)]
pub struct ConnectorManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub tier: String,
    pub transport: String,
    pub tools: Vec<ToolSpec>,
}

fn default_connector_dirs() -> Vec<PathBuf> {
    let mut dirs = vec![
        PathBuf::from("/usr/lib/ariaos/connectors"),
        PathBuf::from("./connectors"),
    ];
    if let Ok(home) = env::var("HOME") {
        dirs.push(PathBuf::from(home).join(".config/ariaos/connectors"));
    }
    dirs
}

fn discover_manifests(search_dirs: &[PathBuf]) -> Vec<ConnectorManifest> {
    let mut manifests = Vec::new();
    for dir in search_dirs {
        let Ok(entries) = fs::read_dir(dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let dir_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if !path.is_dir() || dir_name.starts_with('_') {
                continue;
            }
            let manifest_path = path.join("manifest.json");
            if let Some(manifest) = load_manifest(&manifest_path) {
                manifests.push(manifest);
            }
        }
    }
    manifests
}

fn load_manifest(path: &Path) -> Option<ConnectorManifest> {
    let raw = fs::read_to_string(path).ok()?;
    serde_json::from_str(&raw).ok()
}

fn main() {
    let dirs = default_connector_dirs();
    let manifests = discover_manifests(&dirs);
    println!("aria-daemon v0.1.0 initialized");
    println!("Discovered {} connector(s):", manifests.len());
    for m in &manifests {
        println!(
            "  - {} v{} [tier={}, transport={}, tools={}]",
            m.id,
            m.version,
            m.tier,
            m.transport,
            m.tools.len()
        );
    }
}

