//! Aria Persistent Neural Memory, Self-Learning Engine & Universal OS Application Indexer.
//!
//! Enables AriaOS to:
//! 1. Automatically index every application installed on the system (`/usr/share/applications/*.desktop`)
//!    alongside the 55+ built-in AriaOS ecosystem suites.
//! 2. Learn custom natural-language commands, workflows, and aliases taught by the user (`aprende: ...`).
//! 3. Track command frequency and execution habits persistently on disk (`neural_memory.json`).

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Stdio};

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct LearnedRule {
    pub trigger: String,
    #[serde(alias = "action")]
    pub target_prompt: String,
    pub hits: u64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct NeuralMemory {
    pub rules: Vec<LearnedRule>,
    pub command_habits: HashMap<String, u64>,
    pub total_interactions: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppCatalogEntry {
    pub id: String,
    pub name: String,
    pub category: String,
    pub binary: String,
    pub keywords: Vec<String>,
}

impl NeuralMemory {
    pub fn memory_file_path() -> PathBuf {
        if let Ok(custom) = env::var("ARIAOS_MEMORY_PATH") {
            return PathBuf::from(custom);
        }
        if let Ok(home) = env::var("HOME") {
            let dir = PathBuf::from(home).join(".local/share/ariaos");
            let _ = fs::create_dir_all(&dir);
            return dir.join("neural_memory.json");
        }
        PathBuf::from("/tmp/ariaos-neural-memory.json")
    }

    pub fn load() -> Self {
        let path = Self::memory_file_path();
        if let Ok(raw) = fs::read_to_string(&path) {
            if let Ok(mut mem) = serde_json::from_str::<NeuralMemory>(&raw) {
                if mem.rules.is_empty() {
                    mem.rules = Self::pretrained_rules();
                }
                return mem;
            }
        }
        let seeded = Self {
            rules: Self::pretrained_rules(),
            command_habits: HashMap::new(),
            total_interactions: 0,
        };
        seeded.save();
        seeded
    }

    pub fn pretrained_rules() -> Vec<LearnedRule> {
        let defaults = [
            ("modo gaming", "activar perfil gaming"),
            ("modo desarrollo", "activar perfil desarrollo"),
            ("modo creativo", "activar perfil creativo"),
            ("modo ahorro extremo", "activar perfil ahorro"),
            ("modo seguridad", "activar perfil seguridad"),
            ("limpieza profunda", "optimizar ram"),
            ("auditoria de seguridad", "estado suite seguridad"),
            ("estado contenedores", "contenedores activos"),
            ("estado virtualizacion", "maquinas virtuales"),
            ("escanear descargas", "analizar virus en descargas"),
            ("organizar descargas", "simular organizacion descargas"),
            ("iniciar streaming", "estado obs"),
            ("estado servidores", "sitios filezilla"),
            ("estado p2p", "estado syncthing"),
            ("resumen git", "estado de git"),
            ("punto de restauracion", "crear snapshot del sistema"),
            ("boveda criptografica", "estado boveda secreta"),
            ("laboratorio ia", "modelos de ia locales"),
            ("escanear mi red", "dispositivos en mi red"),
            ("acelerar arranque", "analizar tiempo de arranque"),
            ("portapapeles", "historial del portapapeles"),
        ];
        defaults
            .iter()
            .map(|(t, a)| LearnedRule {
                trigger: (*t).to_string(),
                target_prompt: (*a).to_string(),
                hits: 1,
            })
            .collect()
    }

    pub fn save(&self) {
        let path = Self::memory_file_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Ok(serialized) = serde_json::to_string_pretty(self) {
            let _ = fs::write(&path, serialized);
        }
    }

    pub fn record_habit(&mut self, category_or_tool: &str) {
        self.total_interactions += 1;
        let counter = self
            .command_habits
            .entry(category_or_tool.to_string())
            .or_insert(0);
        *counter += 1;
        self.save();
    }

    pub fn learn_rule(&mut self, trigger: &str, target_prompt: &str) {
        let clean_trigger = trigger.trim().to_lowercase();
        let clean_target = target_prompt.trim().to_string();
        if clean_trigger.is_empty() || clean_target.is_empty() {
            return;
        }
        if let Some(existing) = self.rules.iter_mut().find(|r| r.trigger == clean_trigger) {
            existing.target_prompt = clean_target;
        } else {
            self.rules.push(LearnedRule {
                trigger: clean_trigger,
                target_prompt: clean_target,
                hits: 0,
            });
        }
        self.save();
    }

    pub fn match_learned_rule(&mut self, user_input: &str) -> Option<String> {
        let lower = user_input.trim().to_lowercase();
        for rule in &mut self.rules {
            if lower == rule.trigger || lower.contains(&rule.trigger) {
                rule.hits += 1;
                let target = rule.target_prompt.clone();
                self.save();
                return Some(target);
            }
        }
        None
    }

    pub fn summary_json(&self) -> Value {
        json!({
            "total_interactions": self.total_interactions,
            "learned_rules_count": self.rules.len(),
            "learned_rules": self.rules,
            "top_habits": self.command_habits,
        })
    }
}

/// Parses natural language teaching requests such as:
/// - "aprende: cuando diga modo codigo -> abrir vscodium"
/// - "aprende que modo juego significa optimizar ram"
/// - "/learn modo trabajo = abrir libreoffice"
pub fn parse_teaching_intent(prompt: &str) -> Option<(String, String)> {
    let trimmed = prompt.trim();
    let lower = trimmed.to_lowercase();

    let body = if let Some(rest) = lower.strip_prefix("/learn ") {
        rest.trim()
    } else if let Some(rest) = lower.strip_prefix("aprende:") {
        rest.trim()
    } else if let Some(rest) = lower.strip_prefix("aprende ") {
        rest.trim()
    } else if let Some(rest) = lower.strip_prefix("enseña:") {
        rest.trim()
    } else if let Some(rest) = lower.strip_prefix("learn:") {
        rest.trim()
    } else {
        return None;
    };

    for sep in ["->", "=>", "=", " haz ", " ejecuta ", " significa "] {
        if let Some((left, right)) = body.split_once(sep) {
            let trigger = left
                .trim()
                .trim_start_matches("que ")
                .trim_start_matches("cuando diga ")
                .trim_start_matches("si digo ")
                .trim_matches(|c: char| c == '"' || c == '\'' || c == '«' || c == '»')
                .trim();
            let target = right
                .trim()
                .trim_matches(|c: char| c == '"' || c == '\'' || c == '«' || c == '»')
                .trim();
            if !trigger.is_empty() && !target.is_empty() {
                return Some((trigger.to_string(), target.to_string()));
            }
        }
    }
    None
}

/// Built-in & dynamically discovered catalog of all applications across AriaOS.
pub fn build_universal_app_catalog() -> Vec<AppCatalogEntry> {
    let builtin: &[(&str, &str, &str, &str, &[&str])] = &[
        // Core AriaOS Native Apps
        ("ariaos-command-bar", "Aria Neural HUD", "System", "aria-command-bar", &["hud", "barra ia", "command bar", "asistente"]),
        ("ariaos-antivirus", "Aria Shield Antivirus", "Security", "ariaos-antivirus", &["antivirus", "escudo", "shield", "clamav", "virus"]),
        ("ariaos-settings", "Centro de Control AriaOS", "System", "ariaos-settings", &["ajustes", "configuracion", "configuración", "settings", "panel de control"]),
        ("ariaos-welcome", "Centro de Bienvenida AriaOS", "System", "ariaos-welcome", &["bienvenida", "welcome", "hub", "centro neuronal"]),
        ("ariaos-monitor", "Monitor de Kernel, GPU y Procesos AriaOS", "System", "ariaos-monitor", &["monitor de sistema", "monitor", "gestor de procesos", "task manager", "monitor gpu", "ariaos-monitor", "administrador de tareas"]),
        ("ariaos-store", "Centro de Software y Paquetes AriaOS", "System", "ariaos-store", &["tienda", "centro de software", "gestor de paquetes", "instalar programas", "store", "ariaos-store", "paquetes"]),
        ("ariaos-automations", "Centro de Automatizaciones y Memoria IA", "System", "ariaos-automations", &["automatizaciones", "tareas programadas", "reglas ia", "memoria ia", "ariaos-automations"]),
        ("ariaos-firewall", "Cortafuegos y Monitor de Conexiones AriaOS", "Security", "ariaos-firewall", &["cortafuegos", "firewall", "monitor de red", "ariaos-firewall"]),
        ("ariaos-installer", "Instalador Gráfico de Sistema AriaOS", "System", "ariaos-installer", &["instalador", "instalar ariaos", "instalar en disco", "ariaos-installer"]),
        ("ariaos-snapshots", "Máquina del Tiempo y Snapshots AriaOS", "System", "ariaos-snapshots", &["snapshots", "time machine", "maquina del tiempo", "máquina del tiempo", "restaurar sistema", "ariaos-snapshots"]),
        ("ariaos-vault", "Bóveda Criptográfica y Gestor de Secretos AriaOS", "Security", "ariaos-vault", &["boveda", "bóveda", "vault", "secretos", "claves", "ariaos-vault"]),
        ("ariaos-ai-studio", "Laboratorio de Modelos e IA Local AriaOS", "System", "ariaos-ai-studio", &["ai studio", "estudio ia", "modelos ia", "cerebro ia", "ariaos-ai-studio"]),
        ("ariaos-netradar", "Radar de Red, Escáner LAN y DNS Privado AriaOS", "Internet", "ariaos-netradar", &["radar de red", "netradar", "escaner lan", "dns seguro", "ariaos-netradar"]),
        ("ariaos-optimizer", "Optimizador de Arranque y Limpiador Profundo AriaOS", "System", "ariaos-optimizer", &["optimizador", "limpiador", "boot analyzer", "ariaos-optimizer"]),
        ("ariaos-clipboard", "Portapapeles Inteligente e Historial Neuronal AriaOS", "System", "ariaos-clipboard", &["portapapeles", "clipboard", "historial copiado", "ariaos-clipboard"]),
        // AriaDE Essential System Utilities (Cupertino Desktop)
        ("thunar", "Gestor de Archivos Thunar", "System", "thunar", &["archivos", "carpetas", "thunar", "explorador", "files", "gestor de archivos", "carpeta"]),
        ("xfce4-terminal", "Terminal de Sistema", "System", "xfce4-terminal", &["terminal", "consola", "shell", "bash", "linea de comandos", "cmd", "consola de comandos"]),
        ("mousepad", "Editor de Texto Mousepad", "Office", "mousepad", &["editor", "bloc de notas", "editor de texto", "notas", "texto", "mousepad"]),
        ("viewnior", "Visor de Imágenes Viewnior", "Multimedia", "viewnior", &["fotos", "imagenes", "imágenes", "visor de fotos", "galeria", "galería", "viewnior"]),
        // Web Browsers & Comms
        ("firefox", "Mozilla Firefox", "Internet", "firefox", &["firefox", "navegador", "browser", "web", "internet"]),
        ("brave-browser", "Brave Browser", "Internet", "brave", &["brave", "navegador brave"]),
        ("thunderbird", "Mozilla Thunderbird", "Internet", "thunderbird", &["thunderbird", "correo", "email", "mail"]),
        ("org.telegram.desktop", "Telegram Desktop", "Internet", "telegram-desktop", &["telegram", "mensajeria"]),
        ("signal-desktop", "Signal Desktop", "Internet", "signal-desktop", &["signal"]),
        ("im.riot.Riot", "Element Matrix Client", "Internet", "element-desktop", &["element", "matrix"]),
        ("discord", "Discord", "Internet", "discord", &["discord", "chat de voz"]),
        ("filezilla", "FileZilla FTP/SFTP", "Internet", "filezilla", &["filezilla", "cliente ftp", "sftp"]),
        ("org.qbittorrent.qBittorrent", "qBittorrent", "Internet", "qbittorrent", &["qbittorrent", "torrent", "torrents"]),
        ("syncthing", "Syncthing", "Internet", "syncthing", &["syncthing", "sincronizacion"]),
        // Development & Containers
        ("codium", "VSCodium IDE", "Development", "codium", &["vscodium", "codium", "vscode", "visual studio code", "ide", "codigo"]),
        ("dbeaver", "DBeaver Database Manager", "Development", "dbeaver", &["dbeaver", "base de datos", "sql client"]),
        ("insomnia", "Insomnia API Client", "Development", "insomnia", &["insomnia", "cliente api", "rest client"]),
        ("virt-manager", "Virtual Machine Manager", "Development", "virt-manager", &["virt-manager", "kvm", "qemu", "maquinas virtuales"]),
        ("virtualbox", "Oracle VirtualBox", "Development", "virtualbox", &["virtualbox", "vbox"]),
        // Creative & Multimedia Suite
        ("gimp", "GNU Image Manipulation Program (GIMP)", "Creative", "gimp", &["gimp", "editor de fotos", "photoshop"]),
        ("org.kde.krita", "Krita Digital Painting", "Creative", "krita", &["krita", "dibujo", "ilustracion", "pintura digital"]),
        ("blender", "Blender 3D Suite", "Creative", "blender", &["blender", "modelado 3d", "animacion 3d"]),
        ("org.inkscape.Inkscape", "Inkscape Vector Graphics", "Creative", "inkscape", &["inkscape", "vectores", "svg"]),
        ("org.darktable.darktable", "Darktable RAW Lab", "Creative", "darktable", &["darktable", "revelado raw"]),
        ("rawtherapee", "RawTherapee", "Creative", "rawtherapee", &["rawtherapee"]),
        ("org.kde.kdenlive", "Kdenlive Video Editor", "Creative", "kdenlive", &["kdenlive", "editor de video", "montaje de video"]),
        ("fr.handbrake.ghb", "HandBrake Video Transcoder", "Creative", "ghb", &["handbrake", "transcodificador", "convertir video"]),
        ("audacity", "Audacity Audio Studio", "Creative", "audacity", &["audacity", "editor de audio", "grabar audio"]),
        ("com.obsproject.Studio", "OBS Studio", "Multimedia", "obs", &["obs", "obs studio", "grabar pantalla", "streaming"]),
        ("vlc", "VLC Media Player", "Multimedia", "vlc", &["vlc", "reproductor de video"]),
        ("mpv", "mpv Media Player", "Multimedia", "mpv", &["mpv"]),
        ("org.kde.elisa", "Elisa Music Player", "Multimedia", "elisa", &["elisa", "reproductor de musica"]),
        ("freetube", "FreeTube", "Multimedia", "freetube", &["freetube", "youtube"]),
        ("stremio", "Stremio", "Multimedia", "stremio", &["stremio"]),
        // Office & Knowledge
        ("libreoffice", "LibreOffice Suite", "Office", "libreoffice", &["libreoffice", "ofimatica", "word", "excel", "writer", "calc", "impress"]),
        ("obsidian", "Obsidian Knowledge Base", "Office", "obsidian", &["obsidian", "notas", "segundo cerebro"]),
        ("calibre", "Calibre E-Book Manager", "Office", "calibre", &["calibre", "ebooks", "libros electronicos"]),
        // Security, Privacy & Pentesting
        ("org.keepassxc.KeePassXC", "KeePassXC Password Vault", "Security", "keepassxc", &["keepass", "keepassxc", "gestor de contraseñas"]),
        ("veracrypt", "VeraCrypt Disk Encryption", "Security", "veracrypt", &["veracrypt", "volumen cifrado"]),
        ("timeshift-gtk", "Timeshift System Snapshots", "Security", "timeshift-gtk", &["timeshift", "copia de seguridad", "punto de restauracion"]),
        ("org.flameshot.Flameshot", "Flameshot Screenshot", "System", "flameshot", &["flameshot", "captura de pantalla", "screenshot"]),
        ("org.wireshark.Wireshark", "Wireshark Network Analyzer", "Security", "wireshark", &["wireshark", "analizador de red", "pcap"]),
        ("ghidra", "Ghidra Reverse Engineering", "Security", "ghidra", &["ghidra", "ingenieria inversa"]),
        ("re.rizin.cutter", "Cutter Reverse Engineering", "Security", "cutter", &["cutter", "rizin"]),
        ("ventoy", "Ventoy USB Creator", "System", "ventoygui", &["ventoy", "crear usb booteable"]),
        // Gaming & Emulation
        ("steam", "Steam Gaming Platform", "Gaming", "steam", &["steam", "juegos"]),
        ("net.lutris.Lutris", "Lutris Gaming Hub", "Gaming", "lutris", &["lutris"]),
        ("heroic", "Heroic Games Launcher", "Gaming", "heroic", &["heroic", "epic games", "gog"]),
        ("org.libretro.RetroArch", "RetroArch Emulator", "Gaming", "retroarch", &["retroarch", "emulador retro"]),
        ("pcsx2-qt", "PCSX2 PS2 Emulator", "Gaming", "pcsx2-qt", &["pcsx2", "playstation 2", "ps2"]),
        ("rpcs3", "RPCS3 PS3 Emulator", "Gaming", "rpcs3", &["rpcs3", "playstation 3", "ps3"]),
        ("duckstation-qt", "DuckStation PS1 Emulator", "Gaming", "duckstation-qt", &["duckstation", "playstation 1", "ps1"]),
    ];

    let mut catalog: Vec<AppCatalogEntry> = builtin
        .iter()
        .map(|(id, name, cat, bin, kw)| AppCatalogEntry {
            id: (*id).to_string(),
            name: (*name).to_string(),
            category: (*cat).to_string(),
            binary: (*bin).to_string(),
            keywords: kw.iter().map(|s| (*s).to_string()).collect(),
        })
        .collect();

    // Dynamically discover additional .desktop entries installed on the OS
    let desktop_dirs = [
        PathBuf::from("/usr/share/applications"),
        PathBuf::from("/usr/local/share/applications"),
    ];
    for dir in desktop_dirs {
        let Ok(entries) = fs::read_dir(&dir) else { continue };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("desktop") {
                continue;
            }
            let Ok(raw) = fs::read_to_string(&path) else { continue };
            if raw.contains("NoDisplay=true") {
                continue;
            }
            let mut name = String::new();
            let mut exec_bin = String::new();
            for line in raw.lines() {
                if name.is_empty() && (line.starts_with("Name[es]=") || line.starts_with("Name=")) {
                    if let Some((_, v)) = line.split_once('=') {
                        name = v.trim().to_string();
                    }
                } else if exec_bin.is_empty() && line.starts_with("Exec=") {
                    if let Some((_, v)) = line.split_once('=') {
                        if let Some(first_tok) = v.split_whitespace().next() {
                            exec_bin = first_tok.trim_matches('"').to_string();
                        }
                    }
                }
            }
            if !name.is_empty() && !exec_bin.is_empty() {
                let already = catalog.iter().any(|c| c.binary == exec_bin);
                if !already {
                    let stem = path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("app")
                        .to_string();
                    let lower_name = name.to_lowercase();
                    catalog.push(AppCatalogEntry {
                        id: stem,
                        name,
                        category: "Installed".to_string(),
                        binary: exec_bin.clone(),
                        keywords: vec![lower_name, exec_bin.to_lowercase()],
                    });
                }
            }
        }
    }

    catalog
}

fn binary_exists(bin: &str) -> bool {
    if bin.starts_with('/') {
        return std::path::Path::new(bin).is_file();
    }
    if let Ok(path) = env::var("PATH") {
        for dir in env::split_paths(&path) {
            if dir.join(bin).is_file() {
                return true;
            }
        }
    }
    for fallback_dir in ["/usr/bin", "/usr/local/bin", "/bin"] {
        if std::path::Path::new(fallback_dir).join(bin).is_file() {
            return true;
        }
    }
    false
}

/// Finds and launches any installed application matching the user's natural language request.
pub fn find_and_launch_app(lower_prompt: &str) -> Option<(String, String)> {
    let catalog = build_universal_app_catalog();
    for entry in &catalog {
        if entry.keywords.iter().any(|kw| lower_prompt.contains(kw)) {
            if binary_exists(&entry.binary) {
                let _ = Command::new(&entry.binary)
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn();
                return Some((entry.name.clone(), entry.binary.clone()));
            }
        }
    }
    None
}

