use crate::manifest::{
    find_tool, ollama_tools_payload, parse_qualified_tool_name, RegisteredConnector,
};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};
use std::env;
use std::time::Duration;

const BASE_SYSTEM_PROMPT: &str = "\
You ARE Aria, the OS itself inside AriaOS (Arch Linux kernel + systemd + KDE Plasma 6). \
You operate natively across every layer of the computer:
- Kernel & Hardware: os-kernel (telemetry, dmesg, PCI/USB, sysctl, kernel modules), os-storage (disks/archives)
- Core System & Security: os-system (systemd/processes), os-packages (pacman), security-antivirus (ClamAV + quarantine), security-vault-crypto, security-net-audit
- File Manager & Desktop Apps: os-files (Dolphin, search, XDG Trash, duplicates, organize), os-desktop, office, media, creative, dev & gaming connectors
Language Directive: You have native multi-language support (English, Spanish, French, German, Italian, Portuguese, Chinese, Japanese). You must always respond fluently in the language matching the user's prompt (or the configured system language).
Rules:\n\
1. Call all read-only tools (risk=read) you need immediately—even multiple tools in sequence—without asking first; aria-daemon enforces confirmation prompts for write and privileged tools.\n\
2. Never guess or fabricate system metrics, kernel state, malware scan outputs, or file counts. Always call the appropriate tool first.\n\
3. When organizing files, prefer dry-run (apply=false) first unless the user explicitly asks to apply changes.\n\
4. Respond concisely in the user's language based strictly on observed tool results.";

fn load_config_value(key: &str) -> Option<Value> {
    let candidates = [
        env::var("ARIAOS_CONFIG_PATH").ok().map(std::path::PathBuf::from),
        env::var("HOME").ok().map(|h| std::path::PathBuf::from(h).join(".config/ariaos/config.json")),
        Some(std::path::PathBuf::from("/etc/ariaos/config.json")),
    ];
    for cand in candidates.into_iter().flatten() {
        if cand.exists() {
            if let Ok(raw) = std::fs::read_to_string(cand) {
                if let Ok(json) = serde_json::from_str::<Value>(&raw) {
                    if let Some(val) = json.get(key) {
                        return Some(val.clone());
                    }
                }
            }
        }
    }
    None
}

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
    pub num_ctx: u64,
    pub temperature: f64,
    agent: ureq::Agent,
}

impl OllamaClient {
    pub fn from_env(model_override: Option<String>) -> Self {
        let base_url = env::var("ARIAOS_OLLAMA_URL")
            .ok()
            .or_else(|| load_config_value("ollama_url").and_then(|v| v.as_str().map(String::from)))
            .unwrap_or_else(|| "http://127.0.0.1:11434".to_string());
        let model = model_override
            .or_else(|| env::var("ARIAOS_MODEL").ok())
            .or_else(|| load_config_value("model").and_then(|v| v.as_str().map(String::from)))
            .unwrap_or_else(|| "qwen2.5:3b".to_string());
        let num_ctx = load_config_value("num_ctx")
            .and_then(|v| v.as_u64())
            .unwrap_or(2048);
        let temperature = load_config_value("temperature")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.3);
        let agent = ureq::AgentBuilder::new()
            .timeout_connect(Duration::from_secs(5))
            .timeout_read(Duration::from_secs(180))
            .build();
        Self {
            base_url,
            model,
            num_ctx,
            temperature,
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
                "num_ctx": self.num_ctx,
                "temperature": self.temperature,
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
    let configured_lang = load_config_value("language")
        .and_then(|v| v.as_str().map(String::from))
        .unwrap_or_else(|| "es".to_string());
    let prompt = format!(
        "{BASE_SYSTEM_PROMPT}\nConfigured system language: {configured_lang}."
    );
    vec![json!({
        "role": "system",
        "content": prompt
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

pub fn filter_tools_for_prompt(connectors: &[RegisteredConnector], prompt: &str) -> Vec<Value> {
    let lower = prompt.to_lowercase();
    let has_word = |terms: &[&str]| terms.iter().any(|&term| lower.contains(term));

    // Conversational greetings and general queries need NO tools, allowing instant LLM response
    let is_pure_chat = has_word(&[
        "hola", "buenos días", "buenos dias", "buenas tardes", "buenas noches",
        "cómo estás", "como estas", "qué tal", "que tal", "quién eres", "quien eres",
        "gracias", "de nada", "adiós", "adios", "hasta luego", "cuéntame", "cuentame",
        "chiste", "poema", "qué es ariaos", "que es ariaos",
    ]) && !has_word(&["analiz", "escanea", "ejecuta", "abre", "instala", "mata", "reinicia", "busca"]);

    if is_pure_chat && prompt.trim().len() < 40 {
        return Vec::new();
    }

    let system_match = has_word(&[
        "sistema", "salud", "cpu", "memoria", "ram", "uptime", "rendimiento",
        "proceso", "procesos", "carga", "top", "servicio", "servicios", "status", "estado",
    ]);

    let kernel_match = has_word(&[
        "kernel", "temperatura", "hardware", "dmesg", "pci", "usb", "módulo", "modulo", "driver", "sysctl",
    ]);

    let storage_match = has_word(&[
        "disco", "particion", "partición", "almacenamiento", "espacio", "tar", "zip", "comprimir", "descomprimir",
    ]);

    let av_match = has_word(&[
        "antivirus", "virus", "clam", "clamav", "malware", "escanear", "infect", "cuarentena", "freshclam",
    ]);

    let files_match = has_word(&[
        "archivo", "archivos", "carpeta", "carpetas", "fichero", "directorio", "buscar archivo", "organizar",
    ]);

    let packages_match = has_word(&[
        "paquete", "paquetes", "programa", "programas", "aplicacion", "aplicación", "aplicaciones",
        "pacman", "instalar", "actualizar", "actualizaciones", "updates", "limpiar cache",
    ]);

    let desktop_match = has_word(&[
        "pantalla", "resolucion", "resolución", "brillo", "fondo", "wallpaper", "tema", "volumen", "audio", "ventana",
    ]);

    let dev_match = has_word(&[
        "git", "repo", "commit", "diff", "docker", "podman", "container", "portainer",
        "vm", "virtualbox", "qemu", "kvm", "virsh", "sql", "database", "bd", "tabla",
        "dbeaver", "workbench", "http", "api", "postman", "insomnia", "vscodium", "codium", "kate", "editor",
    ]);

    let creative_match = has_word(&[
        "imagen", "image", "foto", "photo", "svg", "vector", "inkscape", "gimp",
        "krita", "blender", "3d", "audacity", "audio", "sonido", "video", "render",
        "transcod", "handbrake", "shotcut", "pitivi", "darktable", "raw", "color",
    ]);

    let office_match = has_word(&[
        "libreoffice", "office", "calc", "writer", "impress", "document", "documento",
        "docx", "odt", "xlsx", "csv", "pdf", "poppler", "okular", "texto",
    ]);

    let browser_match = has_word(&[
        "web", "browser", "navegador", "url", "http", "sitio", "página", "pagina",
        "link", "enlace", "tab", "pestaña", "pestana", "bookmark", "marcador", "brave", "firefox",
    ]);

    let comms_gaming_match = has_word(&[
        "mail", "correo", "email", "thunderbird", "filezilla", "ftp", "sftp",
        "torrent", "qbittorrent", "sync", "syncthing", "telegram", "element", "signal",
        "discord", "steam", "juego", "game", "lutris", "retroarch", "emula", "pcsx", "rpcs", "duckstation",
    ]);

    let security_match = has_word(&[
        "clave", "password", "pass", "contraseña", "contrasena", "keepass", "vault",
        "cifrad", "encrypt", "veracrypt", "snapshot", "timeshift", "captura", "screenshot",
        "flameshot", "wireshark", "pcap", "paquete", "packet", "nmap", "port", "puerto",
        "vulnerab", "exploit", "metasploit", "ghidra", "cutter", "rizin", "hashcat", "john",
    ]);

    let knowledge_match = has_word(&[
        "nota", "note", "obsidian", "bóveda", "boveda", "markdown", "libro", "book", "calibre", "epub",
    ]);

    let mut selected: Vec<&RegisteredConnector> = Vec::new();
    for conn in connectors {
        let id = conn.manifest.id.as_str();

        if (id == "os-system" && system_match)
            || (id == "os-kernel" && kernel_match)
            || (id == "os-storage" && storage_match)
            || (id == "security-antivirus" && av_match)
            || (id == "os-files" && files_match)
            || (id == "os-packages" && packages_match)
            || (id == "os-desktop" && desktop_match)
        {
            selected.push(conn);
        } else if id.starts_with("dev-") && dev_match {
            selected.push(conn);
        } else if (id.starts_with("creative-") || id.starts_with("multimedia-")) && creative_match {
            selected.push(conn);
        } else if id.starts_with("office-") && office_match {
            selected.push(conn);
        } else if id == "browser-web" && browser_match {
            selected.push(conn);
        } else if (id.starts_with("net-") || id.starts_with("comms-")) && comms_gaming_match {
            selected.push(conn);
        } else if id.starts_with("security-") && (security_match || av_match) {
            selected.push(conn);
        } else if id.starts_with("knowledge-") && knowledge_match {
            selected.push(conn);
        }
    }

    // If no tools match the prompt intent, return empty to let the LLM reply naturally and fast.
    if selected.is_empty() {
        return Vec::new();
    }

    let mut tools = Vec::new();
    for conn in selected {
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

    let tools = filter_tools_for_prompt(connectors, user_prompt);
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

