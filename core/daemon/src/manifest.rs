use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RiskLevel {
    Read,
    Write,
    Privileged,
}

impl RiskLevel {
    pub fn as_str(self) -> &'static str {
        match self {
            RiskLevel::Read => "read",
            RiskLevel::Write => "write",
            RiskLevel::Privileged => "privileged",
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ToolSpec {
    pub name: String,
    pub description: String,
    pub risk_level: RiskLevel,
    #[serde(default)]
    pub reversible: bool,
    pub input_schema: Value,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ConnectorManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    #[serde(default)]
    pub description: String,
    pub tier: String,
    pub transport: String,
    #[serde(default)]
    pub entrypoint: Vec<String>,
    pub tools: Vec<ToolSpec>,
}

#[derive(Debug, Clone)]
pub struct RegisteredConnector {
    pub manifest: ConnectorManifest,
    pub root_dir: PathBuf,
}

pub fn default_connector_dirs() -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    if let Ok(custom) = env::var("ARIAOS_CONNECTORS_DIR") {
        dirs.push(PathBuf::from(custom));
    }
    dirs.push(PathBuf::from("./connectors"));
    if let Ok(home) = env::var("HOME") {
        dirs.push(PathBuf::from(home).join(".config/ariaos/connectors"));
    }
    dirs.push(PathBuf::from("/usr/lib/ariaos/connectors"));
    dirs
}

pub fn discover_connectors(search_dirs: &[PathBuf]) -> Vec<RegisteredConnector> {
    let mut found = Vec::new();
    let mut seen_ids = HashSet::new();

    for dir in search_dirs {
        let Ok(entries) = fs::read_dir(dir) else {
            continue;
        };
        let mut subdirs: Vec<PathBuf> = entries
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();
        subdirs.sort();

        for path in subdirs {
            let dir_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if dir_name.starts_with('_') {
                continue;
            }
            let manifest_path = path.join("manifest.json");
            if let Some(manifest) = load_manifest(&manifest_path) {
                if seen_ids.insert(manifest.id.clone()) {
                    found.push(RegisteredConnector {
                        manifest,
                        root_dir: path,
                    });
                }
            }
        }
    }
    found
}

fn load_manifest(path: &Path) -> Option<ConnectorManifest> {
    let raw = fs::read_to_string(path).ok()?;
    serde_json::from_str(&raw).ok()
}

pub fn find_tool<'a>(
    connectors: &'a [RegisteredConnector],
    connector_id: &str,
    tool_name: &str,
) -> Option<(&'a RegisteredConnector, &'a ToolSpec)> {
    let conn = connectors.iter().find(|c| c.manifest.id == connector_id)?;
    let tool = conn.manifest.tools.iter().find(|t| t.name == tool_name)?;
    Some((conn, tool))
}

pub fn parse_qualified_tool_name(qualified: &str) -> Option<(&str, &str)> {
    qualified.split_once("__")
}

/// Convert runnable stdio connectors into Ollama tool definitions.
#[allow(dead_code)]
pub fn ollama_tools_payload(connectors: &[RegisteredConnector]) -> Vec<Value> {
    let mut tools = Vec::new();
    for conn in connectors {
        if conn.manifest.transport != "stdio" || conn.manifest.entrypoint.is_empty() {
            continue;
        }
        for tool in &conn.manifest.tools {
            let fn_name = format!("{}__{}", conn.manifest.id, tool.name);
            let desc = format!(
                "[{} | risk={}] {}",
                conn.manifest.name,
                tool.risk_level.as_str(),
                tool.description
            );
            tools.push(json!({
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": desc,
                    "parameters": tool.input_schema
                }
            }));
        }
    }
    tools
}

