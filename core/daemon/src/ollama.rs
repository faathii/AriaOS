use crate::manifest::{
    find_tool, ollama_tools_payload, parse_qualified_tool_name, RegisteredConnector,
};
use crate::policy::{audit_log, check_approval, ApprovalMode};
use crate::rpc::call_stdio_tool;
use serde_json::{json, Value};
use std::env;
use std::time::Duration;

const BASE_SYSTEM_PROMPT: &str = "\
You ARE Aria, the OS itself inside AriaOS Cyber Obsidian (Arch Linux kernel + Rust Neural Core + KDE Plasma 6). \
You operate natively across all 32 system connectors, 118 API tools, and 58+ applications:
- Kernel, Power & Automation: os-kernel (telemetry, dmesg, PCI/USB, sysctl, modprobe), os-power-modes (list_work_modes, apply_work_mode, gpu_telemetry), os-automation (list_automations, teach_rule, delete_rule, configure_schedule)
- System, Desktop, Storage & Packages: os-system (system_health_summary, list_top_processes, service_status, restart_service), os-desktop (desktop_environment_info, send_notification, launch_application, set_volume, set_brightness, network_status), os-storage (list_block_devices, inspect_archive, create_archive, extract_archive), os-packages (list_installed_packages, search_packages, check_system_updates, clean_package_cache, install_package)
- File Manager (Dolphin): os-files (scan_directory, search_files, file_info, find_duplicates, organize_directory, move_to_trash, open_in_dolphin)
- Security, Antivirus, Vault & Pentesting: security-antivirus (av_status, av_scan_path, av_update_signatures, av_quarantine_list, av_quarantine_file, av_restore_file, av_get_config, av_read_logs, av_set_exclusion, av_shield_control), security-vault-crypto (keepassxc_check_db, veracrypt_list_volumes, timeshift_list_snapshots, flameshot_capture), security-net-audit (security_suite_status, inspect_binary, inspect_pcap, nmap_scan)
- Development, Containers, VMs & Databases: dev-git (repo_status, repo_log, repo_diff, stage_and_commit), dev-vscodium (list_extensions, open_in_editor), dev-containers-vm (container_list, container_logs, vm_list, vm_power), dev-api-databases (http_get_preview, list_db_connections, launch_dev_client)
- Creative, Multimedia & Streaming: creative-gimp, creative-krita, creative-blender, creative-audacity, creative-kdenlive, creative-design-photo, creative-video-transcode, multimedia-ffmpeg, media-obs (OBS WebSocket v5), media-players (MPRIS2 D-Bus VLC/Elisa)
- Office, Knowledge, Web, Comms & Gaming: office-libreoffice, office-okular, knowledge-notes-ebooks (Obsidian/Calibre), browser-web (CDP/bookmarks), comms-thunderbird, net-filezilla, net-sync-comms-gaming (Syncthing, qBittorrent, Steam, Lutris, RetroArch, PCSX2, RPCS3, DuckStation)
Language Directive: Respond fluently in the user's language (Spanish by default).
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
    pub num_thread: usize,
    pub temperature: f64,
    agent: ureq::Agent,
}

impl OllamaClient {
    pub fn from_env(model_override: Option<String>) -> Self {
        let hw = crate::kernel::KernelTelemetry::collect();
        let base_url = env::var("ARIAOS_OLLAMA_URL")
            .ok()
            .or_else(|| load_config_value("ollama_url").and_then(|v| v.as_str().map(String::from)))
            .unwrap_or_else(|| "http://127.0.0.1:11434".to_string());
        let model = model_override
            .or_else(|| env::var("ARIAOS_MODEL").ok())
            .or_else(|| load_config_value("model").and_then(|v| v.as_str().map(String::from)))
            .unwrap_or_else(|| "aria-core".to_string());
        let num_ctx = load_config_value("num_ctx")
            .and_then(|v| v.as_u64())
            .unwrap_or_else(|| hw.hardware_tier.recommended_num_ctx());
        let num_thread = hw.hardware_tier.recommended_threads(hw.cpu_cores);
        let temperature = load_config_value("temperature")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.2);
        let agent = ureq::AgentBuilder::new()
            .timeout_connect(Duration::from_millis(800))
            .timeout_read(Duration::from_secs(25))
            .build();
        Self {
            base_url,
            model,
            num_ctx,
            num_thread,
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
                "num_thread": self.num_thread,
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

    let power_match = has_word(&[
        "modo", "perfil", "gaming", "ahorro", "bateria", "batería", "gpu", "vram", "grafica", "gráfica",
    ]);

    let automation_match = has_word(&[
        "automatiza", "programada", "regla", "aprende", "memoria", "rutina", "timer", "cron",
    ]);

    let mut selected: Vec<&RegisteredConnector> = Vec::new();
    for conn in connectors {
        let id = conn.manifest.id.as_str();

        if (id == "os-system" && system_match)
            || (id == "os-kernel" && kernel_match)
            || (id == "os-power-modes" && (power_match || kernel_match || system_match))
            || (id == "os-automation" && automation_match)
            || (id == "os-storage" && storage_match)
            || (id == "security-antivirus" && av_match)
            || (id == "os-files" && files_match)
            || (id == "os-packages" && packages_match)
            || (id == "os-desktop" && desktop_match)
        {
            selected.push(conn);
        } else if id.starts_with("dev-") && dev_match {
            selected.push(conn);
        } else if (id.starts_with("creative-") || id.starts_with("multimedia-") || id.starts_with("media-")) && creative_match {
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
    // Tier-0: Native Kernel & OS Reflex Engine (<1ms latency, 0 external RAM overhead)
    if approved_tools.is_empty() {
        if let Some(instant_reply) = crate::neural::try_neural_reflex(user_prompt, connectors) {
            return Ok(AgentTurnOutcome::Answered(instant_reply));
        }
    }

    // Check kernel memory pressure before waking external LLM weights
    let telemetry = crate::kernel::KernelTelemetry::collect();
    if telemetry.mem_usage_pct >= 92 {
        let _ = crate::kernel::optimize_kernel_memory();
        let fallback = crate::neural::synthesize_offline_neural_reply(user_prompt, connectors);
        return Ok(AgentTurnOutcome::Answered(fallback));
    }

    history.push(json!({
        "role": "user",
        "content": user_prompt
    }));

    let tools = filter_tools_for_prompt(connectors, user_prompt);
    let max_iterations = 6;

    for _ in 0..max_iterations {
        let reply = match client.chat(history, &tools) {
            Ok(r) => r,
            Err(_err) => {
                // Graceful fallback to embedded Neural Core so the OS never hangs or fails
                let fallback = crate::neural::synthesize_offline_neural_reply(user_prompt, connectors);
                return Ok(AgentTurnOutcome::Answered(fallback));
            }
        };
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

