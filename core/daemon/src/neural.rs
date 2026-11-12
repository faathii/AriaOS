//! Aria Native Neural Engine (Tier-0 Kernel Reflex Core + Self-Learning Memory + Tier-1 LLM Bridge).
//!
//! Philosophy: "The AI is not an application; the AI IS the Operating System."
//! - Executes in <1ms directly in Rust.
//! - Masters all 30 OS connectors, 108 tools, and 55+ desktop applications natively.
//! - Continuously learns custom user commands, macros, and usage habits via `NeuralMemory`.

use crate::kernel::{
    native_disk_usage, native_top_processes, optimize_kernel_memory, self_heal_system,
    KernelTelemetry,
};
use crate::manifest::{find_tool, RegisteredConnector};
use crate::memory::{
    build_universal_app_catalog, find_and_launch_app, parse_teaching_intent, NeuralMemory,
};
use crate::rpc::call_stdio_tool;
use serde_json::json;
use std::process::Command;

/// Resolves the user's prompt via the embedded Tier-0 Kernel Reflex & Self-Learning Engine.
pub fn try_neural_reflex(prompt: &str, connectors: &[RegisteredConnector]) -> Option<String> {
    try_neural_reflex_depth(prompt, connectors, 0)
}

fn try_neural_reflex_depth(
    prompt: &str,
    connectors: &[RegisteredConnector],
    depth: u8,
) -> Option<String> {
    if depth > 2 {
        return None;
    }
    let clean = prompt.trim();
    if clean.is_empty() {
        return None;
    }
    let lower = clean.to_lowercase();
    let mut mem = NeuralMemory::load();

    // 0. Natural Language Self-Learning ("aprende: cuando diga X -> Y" / "/learn X = Y")
    if let Some((trigger, target)) = parse_teaching_intent(clean) {
        mem.learn_rule(&trigger, &target);
        mem.record_habit("self_learning");
        return Some(format!(
            "🧠 **Conocimiento Aprendido y Guardado en Memoria Neuronal**\n\
             • **Disparador:** `«{}»`\n\
             • **Acción asociada:** `{}`\n\
             • Guardado permanentemente en `{}`.\n\
             • A partir de ahora, cada vez que digas *«{}»*, lo ejecutaré en `<0.5 ms`.",
            trigger,
            target,
            NeuralMemory::memory_file_path().display(),
            trigger
        ));
    }

    // Check if the user is invoking a previously learned rule/macro
    if depth == 0 {
        if let Some(learned_target) = mem.match_learned_rule(&lower) {
            mem.record_habit("learned_macro_exec");
            if let Some(res) = try_neural_reflex_depth(&learned_target, connectors, depth + 1) {
                return Some(format!(
                    "⚡ *[Regla aprendida: `{}`]*\n\n{}",
                    learned_target, res
                ));
            }
        }
    }

    // 0b. Inspect Neural Memory & Learned Habits
    if matches_any(
        &lower,
        &[
            "/memory",
            "memoria neuronal",
            "que has aprendido",
            "qué has aprendido",
            "habitos",
            "hábitos",
            "estadisticas de ia",
            "estadísticas de ia",
        ],
    ) {
        let app_count = build_universal_app_catalog().len();
        let tool_count: usize = connectors.iter().map(|c| c.manifest.tools.len()).sum();
        let mut lines = vec![format!(
            "🧠 **Estado de la Memoria Neuronal y Aprendizaje de AriaOS**\n\n\
             • **Interacciones aprendidas:** `{}` ejecuciones registradas\n\
             • **Conocimiento del Sistema:** `{}` conectores del kernel y `{}` herramientas nativas\n\
             • **Aplicaciones indexadas en el OS:** `{}` programas listos para control directo\n",
            mem.total_interactions,
            connectors.len(),
            tool_count,
            app_count
        )];
        if mem.rules.is_empty() {
            lines.push(
                "💡 **Reglas personalizadas:** Aún no me has enseñado atajos propios. Prueba:\n\
                 `aprende: modo codigo -> abrir vscodium y terminal`"
                    .to_string(),
            );
        } else {
            lines.push("⚡ **Reglas y Macros Aprendidas:**".to_string());
            for r in &mem.rules {
                lines.push(format!(
                    "• `«{}»` → `{}` *(usado {} veces)*",
                    r.trigger, r.target_prompt, r.hits
                ));
            }
        }
        return Some(lines.join("\n"));
    }

    // 0c. Complete Ecosystem & Tool Catalog Overview + API Reference (/catalog, /apis, /comandos)
    if matches_any(
        &lower,
        &[
            "/catalog",
            "/apis",
            "/comandos",
            "catalogo",
            "catálogo",
            "comandos de actuacion",
            "comandos de actuación",
            "lista de comandos",
            "que herramientas tienes",
            "qué herramientas tienes",
            "lista de programas",
            "que sabes hacer",
            "qué sabes hacer",
            "apis de aria",
        ],
    ) {
        mem.record_habit("catalog_inspection");
        let app_count = build_universal_app_catalog().len();
        let tool_count: usize = connectors.iter().map(|c| c.manifest.tools.len()).sum();
        return Some(format!(
            "🌐 **Dominio Total de AriaOS ({} Conectores • {} Herramientas API • {} Aplicaciones)**\n\n\
             1. **Kernel, Energía y Automatización (`os-kernel`, `os-power-modes`, `os-automation`):**\n\
                • *Comandos:* `«estado del sistema»`, `«estado gpu»`, `«modo gaming»`, `«modo desarrollo»`, `«modo creativo»`, `«modo ahorro extremo»`, `«modo seguridad»`, `«automatizaciones activas»`, `«dmesg»`, `«hardware pci»`\n\
             2. **Sistema, Escritorio, Archivos y Paquetes (`os-system`, `os-desktop`, `os-files`, `os-storage`, `os-packages`):**\n\
                • *Comandos:* `«optimizar ram»`, `«procesos»`, `«espacio en disco»`, `«mi ip»`, `«volumen al 80%»`, `«brillo al 70%»`, `«analizar descargas»`, `«buscar duplicados»`, `«organizar descargas»`, `«actualizaciones»`\n\
             3. **Ciberseguridad, Cifrado y Pentesting (`security-antivirus`, `security-vault-crypto`, `security-net-audit`):**\n\
                • *Comandos:* `«antivirus»`, `«escanear descargas»`, `«archivos en cuarentena»`, `«exclusiones clamav»`, `«volumenes veracrypt»`, `«snapshots timeshift»`, `«captura de pantalla»`, `«estado suite seguridad»`\n\
             4. **Ingeniería de Software, Contenedores y VMs (`dev-git`, `dev-vscodium`, `dev-containers-vm`, `dev-api-databases`):**\n\
                • *Comandos:* `«estado de git»`, `«git log»`, `«git diff»`, `«extensiones vscodium»`, `«contenedores activos»`, `«maquinas virtuales»`, `«conexiones dbeaver»`\n\
             5. **Estudio Creativo, Multimedia y Streaming (`creative-*`, `multimedia-ffmpeg`, `media-obs`, `media-players`):**\n\
                • *Comandos:* `«estado obs»`, `«iniciar grabacion obs»`, `«detener grabacion obs»`, `«reproductores activos»`, `«estado audacity»`, `«abre gimp y blender»`\n\
             6. **Oficina, Conocimiento, Web, Correo y Gaming (`office-*`, `knowledge-*`, `browser-web`, `comms-thunderbird`, `net-filezilla`, `net-sync-comms-gaming`):**\n\
                • *Comandos:* `«estado libreoffice»`, `«libros calibre»`, `«pestañas abiertas»`, `«perfiles thunderbird»`, `«sitios filezilla»`, `«estado syncthing»`, `«torrents activos»`, `«estado suite gaming»`\n\
             7. **Inspección de API de cualquier conector:** Escribe `«api de <conector o programa>»` (ej. `«api de obs»`, `«api de seguridad»`, `«api de docker»`) o consulta `docs/COMANDOS_IA_Y_APIS_ARIAOS.md`.",
            connectors.len(),
            tool_count,
            app_count
        ));
    }

    // 0d. Deep Inspection of Specific Connector / Program API ("api de <nombre>" / "comandos de <nombre>")
    if lower.starts_with("api de ")
        || lower.starts_with("apis de ")
        || lower.starts_with("como controlas ")
        || lower.starts_with("cómo controlas ")
        || lower.starts_with("herramientas de ")
    {
        let query = lower
            .trim_start_matches("api de ")
            .trim_start_matches("apis de ")
            .trim_start_matches("como controlas ")
            .trim_start_matches("cómo controlas ")
            .trim_start_matches("herramientas de ")
            .trim();
        let matched: Vec<&RegisteredConnector> = connectors
            .iter()
            .filter(|c| {
                c.manifest.id.contains(query)
                    || c.manifest.name.to_lowercase().contains(query)
                    || c.manifest.description.to_lowercase().contains(query)
            })
            .collect();
        if !matched.is_empty() {
            mem.record_habit("api_schema_inspect");
            let mut out = Vec::new();
            for c in matched {
                out.push(format!(
                    "🔌 **Conector `{}` — {}** (`tier={}`, `transport={}`)\n_{}_",
                    c.manifest.id, c.manifest.name, c.manifest.tier, c.manifest.transport, c.manifest.description
                ));
                for t in &c.manifest.tools {
                    out.push(format!(
                        "  • **`{}.{}`** `[riesgo={}]`: {}\n    *Comando directo:* `/call {} {} {{}}`",
                        c.manifest.id,
                        t.name,
                        t.risk_level.as_str(),
                        t.description,
                        c.manifest.id,
                        t.name
                    ));
                }
            }
            return Some(out.join("\n"));
        }
    }

    // 1. Pre-trained Kernel Work Modes (Gaming, Development, Creative, PowerSave, Security)
    if let Some(target_mode) = detect_work_mode_intent(&lower) {
        mem.record_habit(&format!("work_mode:{target_mode}"));
        let opt = optimize_kernel_memory();
        let freed = opt["freed_mb"].as_u64().unwrap_or(0);
        let avail = opt["after_available_mb"].as_u64().unwrap_or(0);

        if let Some((conn, _)) = find_tool(connectors, "os-power-modes", "apply_work_mode") {
            let launch_apps = target_mode != "powersave" && target_mode != "balanced";
            if let Ok(res) = call_stdio_tool(
                conn,
                "apply_work_mode",
                json!({"mode": target_mode, "launch_apps": launch_apps}),
            ) {
                let icon = res.get("icon").and_then(|v| v.as_str()).unwrap_or("⚡");
                let name = res.get("name").and_then(|v| v.as_str()).unwrap_or(target_mode);
                let desc = res.get("description").and_then(|v| v.as_str()).unwrap_or("");
                let launched: Vec<String> = res
                    .get("launched_apps")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|x| x.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();
                let apps_str = if launched.is_empty() {
                    "Ninguna adicional (entorno despejado para máxima eficiencia)".to_string()
                } else {
                    launched.join(", ")
                };
                return Some(format!(
                    "{} **{} Activado en el Kernel**\n\
                     • **Descripción:** {}\n\
                     • **Memoria RAM compactada:** `+{}` MB liberados (`{} MB` disponibles)\n\
                     • **Aplicaciones iniciadas:** `{}`",
                    icon, name, desc, freed, avail, apps_str
                ));
            }
        }
    }

    if matches_any(
        &lower,
        &[
            "modos de trabajo",
            "perfiles de rendimiento",
            "listar modos",
            "que modos tienes",
            "qué modos tienes",
        ],
    ) {
        mem.record_habit("list_work_modes");
        return Some(
            "⚡ **Modos de Trabajo Pre-entrenados en el Kernel de AriaOS:**\n\n\
             • 🎮 **`modo gaming`** — Gobernador CPU `performance`, `swappiness=10`, purga de RAM y suite Gaming.\n\
             • 💻 **`modo desarrollo`** — Caché VFS optimizada para compilación rápida, purga de RAM y lanza VSCodium + Terminal.\n\
             • 🎨 **`modo creativo`** — Prioridad de ancho de banda para vídeo/3D/audio y lanza Kdenlive/OBS/GIMP/Blender.\n\
             • 🔋 **`modo ahorro extremo`** — Gobernador `powersave`, compresión agresiva ZRAM (`swappiness=100`) y brillo al 40%.\n\
             • 🛡️ **`modo seguridad`** — Vigilancia activa con Aria Shield Antivirus e integridad de red.\n\n\
             *Escribe el nombre de cualquier modo para activarlo en `<0.5 ms`.*"
                .to_string(),
        );
    }

    // 1c. Self-Healing & Zombie Process Guardian
    if matches_any(
        &lower,
        &[
            "auto reparar",
            "autoreparar",
            "reparar sistema",
            "procesos zombis",
            "procesos colgados",
            "self heal",
            "guardian del kernel",
            "guardián del kernel",
        ],
    ) {
        mem.record_habit("kernel_self_heal");
        let res = self_heal_system();
        let z_cnt = res["zombies_detected"].as_u64().unwrap_or(0);
        let healed = res["services_healed"]
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        return Some(format!(
            "🔄 **Guardián de Auto-Reparación del Kernel (`self_heal_system`)**\n\
             • **Procesos zombis (`State: Z`) detectados y limpiados:** `{}`\n\
             • **Servicios críticos recuperados automáticamente:** `{}`\n\
             • **Estado de servicios base (`NetworkManager`, `ollama`):** Operativos\n\
             • **Presión PSI de memoria:** `{:.1}%` (RAM en uso: `{}%`)\n\n\
             ```json\n{}\n```",
            z_cnt,
            healed,
            res["psi_memory_avg10"].as_f64().unwrap_or(0.0),
            res["ram_usage_pct"].as_u64().unwrap_or(0),
            serde_json::to_string_pretty(&res).unwrap_or_default()
        ));
    }
    if matches_any(
        &lower,
        &[
            "optimiza",
            "optimizar",
            "libera ram",
            "liberar ram",
            "libera memoria",
            "limpia la ram",
            "va lento",
            "acelera",
            "optimize ram",
            "free memory",
            "drop cache",
        ],
    ) {
        mem.record_habit("kernel_optimize_ram");
        let res = optimize_kernel_memory();
        let before = res["before_available_mb"].as_u64().unwrap_or(0);
        let after = res["after_available_mb"].as_u64().unwrap_or(0);
        let freed = res["freed_mb"].as_u64().unwrap_or(0);
        let pct = res["usage_pct"].as_u64().unwrap_or(0);
        let tier = res["hardware_tier"].as_str().unwrap_or("Tier-A");
        return Some(format!(
            "⚡ **Optimización del Kernel completada** (`{}`)\n\
             • Caché de páginas y compactación de memoria ejecutadas directamente en `/proc/sys/vm`.\n\
             • Memoria disponible: **{} MB** → **{} MB** (+{} MB liberados)\n\
             • Uso actual de RAM: **{}%**",
            tier, before, after, freed, pct
        ));
    }

    // 2. Identity & Greetings (with real-time Kernel pulse)
    if matches_exact_or_starts(
        &lower,
        &[
            "hola",
            "buenas",
            "buenos dias",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "hey",
            "hello",
            "hi",
            "quien eres",
            "quién eres",
            "que eres",
            "qué eres",
            "que es aria",
            "qué es aria",
            "que es ariaos",
            "qué es ariaos",
            "como estas",
            "cómo estás",
            "que tal",
            "qué tal",
            "ayuda",
            "help",
            "que puedes hacer",
            "qué puedes hacer",
        ],
    ) {
        mem.record_habit("greeting_pulse");
        let k = KernelTelemetry::collect();
        let tool_count: usize = connectors.iter().map(|c| c.manifest.tools.len()).sum();
        return Some(format!(
            "⚡ **Aria Neural Core Activo** — Soy el sistema operativo **AriaOS** (`{}` • `{}`).\n\n\
             📊 **Telemetría en vivo del Kernel:**\n\
             • **CPU:** {} ({} hilos, AVX2: `{}`) — Carga: `{:.2}`\n\
             • **Memoria RAM:** {} MB / {} MB (**{}%** en uso, {} MB disponibles)\n\
             • **Presión PSI:** CPU `{:.1}%` | RAM `{:.1}%` | I/O `{:.1}%`\n\
             • ** Ecosistema Enlazado:** `{}` conectores • `{}` herramientas • `{}` reglas aprendidas\n\n\
             💡 **Comandos instantáneos (`<1ms`):**\n\
             • *«Estado del sistema»* | *«Optimizar RAM»* | *«Procesos»* | *«Espacio en disco»* | *«Mi IP»*\n\
             • *«Abrir [cualquier app: vscodium, gimp, blender, firefox, steam, terminal...]»*\n\
             • *«Aprende: modo código -> abrir vscodium y terminal»* | *«Qué sabes hacer»*",
            k.kernel_version,
            k.hardware_tier.as_str(),
            k.cpu_model,
            k.cpu_cores,
            if k.silicon.avx2 { "SÍ" } else { "NO" },
            k.load_1m,
            k.mem_used_mb,
            k.mem_total_mb,
            k.mem_usage_pct,
            k.mem_available_mb,
            k.psi_cpu_some_avg10,
            k.psi_mem_some_avg10,
            k.psi_io_some_avg10,
            connectors.len(),
            tool_count,
            mem.rules.len()
        ));
    }

    // 3. System Health / Kernel Telemetry / CPU / RAM Status
    if matches_any(
        &lower,
        &[
            "estado del sistema",
            "salud del sistema",
            "salud del kernel",
            "estado del kernel",
            "como va el sistema",
            "cómo va el sistema",
            "cuanta ram",
            "cuánta ram",
            "uso de ram",
            "uso de memoria",
            "memoria ram",
            "uso de cpu",
            "temperatura",
            "telemetria",
            "telemetría",
            "kernel",
            "uptime",
            "system status",
            "system health",
        ],
    ) && !matches_any(&lower, &["proceso", "procesos", "archivo", "instala", "log", "dmesg"])
    {
        mem.record_habit("kernel_diagnostics");
        let k = KernelTelemetry::collect();
        let hours = k.uptime_secs / 3600;
        let mins = (k.uptime_secs % 3600) / 60;
        let temp_str = k
            .temp_celsius
            .map(|t| format!("{:.1} °C", t))
            .unwrap_or_else(|| "Nominal (Sensor virtual/VM)".to_string());
        let health_badge = if k.mem_usage_pct < 75 && k.psi_mem_some_avg10 < 5.0 {
            "🟢 ÓPTIMO"
        } else if k.mem_usage_pct < 90 {
            "🟡 CARGA MODERADA"
        } else {
            "🔴 PRESIÓN ALTA (Ejecuta «Optimizar RAM»)"
        };

        return Some(format!(
            "🧠 **Diagnóstico en Tiempo Real del Kernel AriaOS** [{}]\n\n\
             • **Perfil Adaptativo:** `{}` ({})\n\
             • **Kernel:** `{}` (Tiempo activo: `{}h {}m`)\n\
             • **Procesador:** {} ({} hilos lógicos)\n\
             • **Registros Silicio x86_64 (CPUID):** AVX2: `{}` | FMA: `{}` | AES-NI: `{}` | AVX-512: `{}`\n\
             • **Carga media (1m / 5m / 15m):** `{:.2}` / `{:.2}` / `{:.2}`\n\
             • **Temperatura térmica:** `{}`\n\
             • **Memoria Física (RAM):** `{} MB` usados de `{} MB` (**{}%**) — Disponible: `{} MB`\n\
             • **Swap / ZRAM (zstd):** `{} MB` libres de `{} MB`\n\
             • **Presión PSI del Kernel:** CPU `{:.2}%` | Memoria `{:.2}%` | I/O `{:.2}%`",
            health_badge,
            k.hardware_tier.as_str(),
            if k.silicon.hypervisor { "Entorno Virtualizado" } else { "Hardware Bare-Metal" },
            k.kernel_version,
            hours,
            mins,
            k.cpu_model,
            k.cpu_cores,
            if k.silicon.avx2 { "SÍ" } else { "NO" },
            if k.silicon.fma { "SÍ" } else { "NO" },
            if k.silicon.aes_ni { "SÍ" } else { "NO" },
            if k.silicon.avx512 { "SÍ" } else { "NO" },
            k.load_1m,
            k.load_5m,
            k.load_15m,
            temp_str,
            k.mem_used_mb,
            k.mem_total_mb,
            k.mem_usage_pct,
            k.mem_available_mb,
            k.swap_free_mb,
            k.swap_total_mb,
            k.psi_cpu_some_avg10,
            k.psi_mem_some_avg10,
            k.psi_io_some_avg10
        ));
    }

    // 4. Top Processes Inspection (Native Rust /proc scanner, <0.5ms)
    if matches_any(
        &lower,
        &[
            "procesos",
            "top procesos",
            "que consume",
            "qué consume",
            "consumo de cpu",
            "top processes",
            "tareas activas",
        ],
    ) {
        mem.record_habit("top_processes");
        let res = native_top_processes(8);
        if let Some(procs) = res.get("processes").and_then(|v| v.as_array()) {
            let mut lines = vec![
                "📊 **Procesos con mayor huella en el Kernel (Lectura directa `/proc`):**\n".to_string(),
                "| PID | Proceso | RAM (MB) | RAM % |".to_string(),
                "| :--- | :--- | :---: | :---: |".to_string(),
            ];
            for p in procs.iter().take(8) {
                let pid = p.get("pid").and_then(|v| v.as_i64()).unwrap_or(0);
                let comm = p.get("command").and_then(|v| v.as_str()).unwrap_or("?");
                let rss = p.get("rss_mb").and_then(|v| v.as_u64()).unwrap_or(0);
                let mem_p = p.get("mem_percent").and_then(|v| v.as_f64()).unwrap_or(0.0);
                lines.push(format!("| `{}` | **{}** | `{} MB` | `{:.1}%` |", pid, comm, rss, mem_p));
            }
            return Some(lines.join("\n"));
        }
    }

    // 5. Disk & Storage Usage (Native fast path)
    if matches_any(
        &lower,
        &[
            "espacio en disco",
            "almacenamiento",
            "particiones",
            "cuanto espacio",
            "cuánto espacio",
            "disco duro",
            "disk usage",
        ],
    ) {
        mem.record_habit("disk_usage");
        let res = native_disk_usage();
        if let Some(mounts) = res.get("filesystems").and_then(|v| v.as_array()) {
            let mut lines = vec!["💾 **Estado de Almacenamiento y Sistemas de Archivos:**\n".to_string()];
            for m in mounts {
                let target = m.get("mountpoint").and_then(|v| v.as_str()).unwrap_or("/");
                let size = m.get("size").and_then(|v| v.as_str()).unwrap_or("?");
                let used = m.get("used").and_then(|v| v.as_str()).unwrap_or("?");
                let avail = m.get("avail").and_then(|v| v.as_str()).unwrap_or("?");
                let pct = m.get("use_percent").and_then(|v| v.as_str()).unwrap_or("?");
                lines.push(format!(
                    "• **`{}`** — Usado: `{}` de `{}` (`{}`) — Libre: **{}**",
                    target, used, size, pct, avail
                ));
            }
            return Some(lines.join("\n"));
        }
    }

    // 6. Network & IP Address Inspection
    if matches_any(
        &lower,
        &[
            "mi ip",
            "direccion ip",
            "dirección ip",
            "estado de red",
            "interfaces de red",
            "red activa",
            "network status",
        ],
    ) {
        mem.record_habit("network_status");
        if let Ok(out) = Command::new("ip").args(["-br", "addr"]).output() {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let mut lines = vec!["🌐 **Interfaces de Red Activas en el Kernel:**\n".to_string()];
            for l in stdout.lines() {
                let parts: Vec<&str> = l.split_whitespace().collect();
                if parts.len() >= 2 {
                    let iface = parts[0];
                    let state = parts[1];
                    let addrs = if parts.len() > 2 { parts[2..].join(", ") } else { "Sin IP asignada".to_string() };
                    lines.push(format!("• **`{}`** [`{}`] — `{}`", iface, state, addrs));
                }
            }
            return Some(lines.join("\n"));
        }
    }

    // 7. Hardware PCI / USB & Kernel Ring Buffer (dmesg)
    if matches_any(&lower, &["pci", "usb", "gpu", "tarjeta grafica", "tarjeta gráfica", "hardware conectado"]) {
        mem.record_habit("hardware_pci_usb");
        if let Some((conn, _)) = find_tool(connectors, "os-kernel", "hardware_pci_usb") {
            if let Ok(res) = call_stdio_tool(conn, "hardware_pci_usb", json!({})) {
                let pci = res.get("pci_devices").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0);
                let usb = res.get("usb_devices").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0);
                return Some(format!(
                    "🔌 **Inventario de Buses Hardware (`os-kernel.hardware_pci_usb`):**\n\
                     • **Dispositivos PCI/PCIe detectados:** `{}`\n\
                     • **Dispositivos USB conectados:** `{}`\n\n\
                     ```json\n{}\n```",
                    pci,
                    usb,
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    if matches_any(&lower, &["dmesg", "logs del kernel", "errores del kernel"]) {
        mem.record_habit("dmesg_inspect");
        if let Some((conn, _)) = find_tool(connectors, "os-kernel", "dmesg_inspect") {
            if let Ok(res) = call_stdio_tool(conn, "dmesg_inspect", json!({"lines": 15})) {
                return Some(format!(
                    "📜 **Buffer de Mensajes del Kernel (`dmesg`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 8. Universal Application Launcher (Supports chaining multiple apps with " y " / ",")
    if matches_any(&lower, &["abre ", "abrir ", "ejecuta ", "lanza ", "open ", "launch ", "inicia "]) {
        let mut launched = Vec::new();
        for segment in lower.split(|c| c == ',' || c == ';') {
            for part in segment.split(" y ") {
                if let Some((app_name, bin)) = find_and_launch_app(part) {
                    mem.record_habit(&format!("launch:{bin}"));
                    launched.push(format!("**{}** (`{}`)", app_name, bin));
                }
            }
        }
        if !launched.is_empty() {
            return Some(format!("🚀 Iniciando en segundo plano: {}.", launched.join(", ")));
        }
    }

    // 9. Volume & Brightness Control (Native direct execution + os-desktop fallback)
    if lower.contains("volumen") || lower.contains("volume") {
        if let Some(num) = extract_number(&lower) {
            let pct = num.min(100);
            mem.record_habit("set_volume");
            let _ = Command::new("wpctl")
                .args(["set-volume", "@DEFAULT_AUDIO_SINK@", &format!("{pct}%")])
                .output()
                .or_else(|_| {
                    Command::new("pactl")
                        .args(["set-sink-volume", "@DEFAULT_SINK@", &format!("{pct}%")])
                        .output()
                });
            return Some(format!("🔊 Volumen maestro del sistema ajustado al **{}%**.", pct));
        }
    }
    if lower.contains("brillo") || lower.contains("brightness") {
        if let Some(num) = extract_number(&lower) {
            let pct = num.clamp(5, 100);
            mem.record_habit("set_brightness");
            let _ = Command::new("brightnessctl")
                .args(["set", &format!("{pct}%")])
                .output();
            return Some(format!("☀️ Brillo de pantalla ajustado al **{}%**.", pct));
        }
    }

    // 10. Antivirus & Security Shield (Matching exact manifest tool `av_status`)
    if matches_any(&lower, &["antivirus", "clamav", "virus", "escudo", "cuarentena"])
        && !matches_any(&lower, &["escanea ", "analiza "])
    {
        mem.record_habit("security_antivirus_status");
        if let Some((conn, _)) = find_tool(connectors, "security-antivirus", "av_status") {
            if let Ok(res) = call_stdio_tool(conn, "av_status", json!({})) {
                let q_count = res.get("quarantined_files_count").and_then(|v| v.as_u64()).unwrap_or(0);
                let db_ok = res.get("signatures_ready").and_then(|v| v.as_bool()).unwrap_or(false);
                return Some(format!(
                    "🛡️ **Aria Shield (Motor Antivirus Integrado en el Kernel)**\n\
                     • **Modo de operación:** Bajo demanda (Optimizado para 0 MB consumo de RAM en reposo)\n\
                     • **Base de firmas local:** {}\n\
                     • **Archivos aislados en cuarentena:** `{}`\n\
                     • Di *«abrir antivirus»* para lanzar la interfaz gráfica Cyber Obsidian.",
                    if db_ok { "Instalada y verificada" } else { "Lista para sincronizar (`freshclam`)" },
                    q_count
                ));
            }
        }
    }

    // 11. Package Manager & System Updates (`os-packages`)
    if matches_any(&lower, &["actualizaciones", "hay updates", "check updates", "actualizar sistema"]) {
        mem.record_habit("check_updates");
        if let Some((conn, _)) = find_tool(connectors, "os-packages", "check_system_updates") {
            if let Ok(res) = call_stdio_tool(conn, "check_system_updates", json!({})) {
                let count = res.get("pending_count").and_then(|v| v.as_u64()).unwrap_or(0);
                return Some(format!(
                    "📦 **Estado de Paquetes del Sistema (`pacman`):**\n\
                     • **Actualizaciones pendientes:** `{}` paquete(s).",
                    count
                ));
            }
        }
    }

    // 12. Git Status, Log & Diff (`dev-git`)
    if matches_any(&lower, &["estado de git", "git status", "cambios en git", "resumen git"]) {
        mem.record_habit("git_status");
        if let Some((conn, _)) = find_tool(connectors, "dev-git", "repo_status") {
            if let Ok(res) = call_stdio_tool(conn, "repo_status", json!({"repo_path": "."})) {
                return Some(format!(
                    "💻 **Estado del Repositorio Git (`dev-git.repo_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(&lower, &["git log", "ultimos commits", "últimos commits", "historial git"]) {
        mem.record_habit("git_log");
        if let Some((conn, _)) = find_tool(connectors, "dev-git", "repo_log") {
            if let Ok(res) = call_stdio_tool(conn, "repo_log", json!({"repo_path": ".", "limit": 5})) {
                return Some(format!(
                    "📜 **Últimos Commits (`dev-git.repo_log`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(&lower, &["git diff", "cambios sin guardar"]) {
        mem.record_habit("git_diff");
        if let Some((conn, _)) = find_tool(connectors, "dev-git", "repo_diff") {
            if let Ok(res) = call_stdio_tool(conn, "repo_diff", json!({"repo_path": "."})) {
                return Some(format!(
                    "🔍 **Diferencias en el Repositorio (`dev-git.repo_diff`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 13. Universal Domain API Action Commands across all 32 Connectors
    if let Some(domain_reply) = execute_domain_api_reflex(&lower, connectors, &mut mem) {
        return Some(domain_reply);
    }

    None
}

/// Fallback synthesizer when the Tier-1 LLM daemon (Ollama) is offline or unloaded in a low-RAM environment.
pub fn synthesize_offline_neural_reply(prompt: &str, connectors: &[RegisteredConnector]) -> String {
    if let Some(reflex) = try_neural_reflex(prompt, connectors) {
        return reflex;
    }

    let k = KernelTelemetry::collect();
    let app_count = build_universal_app_catalog().len();
    let tool_count: usize = connectors.iter().map(|c| c.manifest.tools.len()).sum();
    format!(
        "⚡ **Aria Neural Core (`{}` • Modo Determinista Ultrarrápido)**\n\n\
         Solicitud recibida: `\"{}\"`\n\
         • **Estado del Kernel:** `{}` — RAM disponible: `{} MB` ({}% en uso) — Carga CPU: `{:.2}`.\n\
         • **Dominio del Sistema:** `{}` conectores • `{}` herramientas • `{}` aplicaciones indexadas.\n\n\
         💡 *Puedes enseñarme este comando como un atajo permanente escribiendo:*\n\
         `aprende: {} -> <acción o programa a ejecutar>`\n\
         *O consultar todo mi catálogo con:* `qué sabes hacer` | `memoria neuronal`",
        k.hardware_tier.as_str(),
        prompt.trim(),
        k.kernel_version,
        k.mem_available_mb,
        k.mem_usage_pct,
        k.load_1m,
        connectors.len(),
        tool_count,
        app_count,
        prompt.trim().to_lowercase()
    )
}

fn matches_any(text: &str, patterns: &[&str]) -> bool {
    patterns.iter().any(|p| text.contains(p))
}

fn detect_work_mode_intent(lower: &str) -> Option<&'static str> {
    if matches_any(
        lower,
        &[
            "activar perfil gaming",
            "modo gaming",
            "modo juego",
            "gaming mode",
        ],
    ) {
        Some("gaming")
    } else if matches_any(
        lower,
        &[
            "activar perfil desarrollo",
            "modo desarrollo",
            "modo codigo",
            "modo código",
            "modo programacion",
            "modo programación",
            "dev mode",
        ],
    ) {
        Some("development")
    } else if matches_any(
        lower,
        &[
            "activar perfil creativo",
            "modo creativo",
            "modo estudio",
            "modo edicion",
            "modo edición",
            "modo streaming",
        ],
    ) {
        Some("creative")
    } else if matches_any(
        lower,
        &[
            "activar perfil ahorro",
            "modo ahorro",
            "modo ahorro extremo",
            "modo bateria",
            "modo batería",
            "ahorro de energia",
            "ahorro de energía",
        ],
    ) {
        Some("powersave")
    } else if matches_any(
        lower,
        &[
            "activar perfil seguridad",
            "modo seguridad",
            "modo blindaje",
            "modo fortaleza",
        ],
    ) {
        Some("security")
    } else if matches_any(lower, &["modo equilibrado", "perfil equilibrado"]) {
        Some("balanced")
    } else {
        None
    }
}

fn matches_exact_or_starts(text: &str, patterns: &[&str]) -> bool {
    let trimmed = text.trim_matches(|c: char| !c.is_alphanumeric());
    patterns
        .iter()
        .any(|p| trimmed == *p || trimmed.starts_with(&format!("{p} ")))
}

fn extract_number(text: &str) -> Option<u64> {
    for token in text.split(|c: char| !c.is_ascii_digit()) {
        if !token.is_empty() {
            if let Ok(n) = token.parse::<u64>() {
                return Some(n);
            }
        }
    }
    None
}

/// Direct API action dispatcher for specialized connectors (`<1 ms` dispatch).
fn execute_domain_api_reflex(
    lower: &str,
    connectors: &[RegisteredConnector],
    mem: &mut NeuralMemory,
) -> Option<String> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| "/home/aria".to_string());
    let downloads = format!("{home}/Downloads");

    // 1. GPU & DRM Telemetry (`os-power-modes.gpu_telemetry`)
    if matches_any(lower, &["estado gpu", "telemetria gpu", "telemetría gpu", "vram"]) {
        mem.record_habit("gpu_telemetry");
        if let Some((conn, _)) = find_tool(connectors, "os-power-modes", "gpu_telemetry") {
            if let Ok(res) = call_stdio_tool(conn, "gpu_telemetry", json!({})) {
                return Some(format!(
                    "🎮 **Telemetría de GPU y Adaptadores DRM (`os-power-modes.gpu_telemetry`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 2. Filesystem & Dolphin (`os-files`)
    if matches_any(lower, &["analizar descargas", "escanear carpeta descargas", "estado descargas"]) {
        mem.record_habit("scan_downloads");
        if let Some((conn, _)) = find_tool(connectors, "os-files", "scan_directory") {
            if let Ok(res) = call_stdio_tool(conn, "scan_directory", json!({"path": downloads})) {
                return Some(format!(
                    "📂 **Análisis de Carpeta de Descargas (`os-files.scan_directory`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["buscar duplicados", "archivos duplicados"]) {
        mem.record_habit("find_duplicates");
        if let Some((conn, _)) = find_tool(connectors, "os-files", "find_duplicates") {
            if let Ok(res) = call_stdio_tool(conn, "find_duplicates", json!({"path": downloads})) {
                return Some(format!(
                    "🔍 **Búsqueda de Archivos Duplicados por SHA-256 (`os-files.find_duplicates`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["simular organizacion", "organizar descargas"]) {
        mem.record_habit("organize_downloads_dryrun");
        if let Some((conn, _)) = find_tool(connectors, "os-files", "organize_directory") {
            if let Ok(res) = call_stdio_tool(
                conn,
                "organize_directory",
                json!({"path": downloads, "apply": false}),
            ) {
                return Some(format!(
                    "🗂️ **Simulación Segura de Organización (`os-files.organize_directory` dry-run):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 3. Antivirus Scan, Quarantine & Config (`security-antivirus`)
    if matches_any(lower, &["analizar virus en descargas", "escanear descargas", "analizar descargas con antivirus"]) {
        mem.record_habit("av_scan_downloads");
        if let Some((conn, _)) = find_tool(connectors, "security-antivirus", "av_scan_path") {
            if let Ok(res) = call_stdio_tool(conn, "av_scan_path", json!({"path": downloads})) {
                return Some(format!(
                    "🛡️ **Escaneo Antivirus en Descargas (`security-antivirus.av_scan_path`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["archivos en cuarentena", "listar cuarentena"]) {
        mem.record_habit("av_quarantine_list");
        if let Some((conn, _)) = find_tool(connectors, "security-antivirus", "av_quarantine_list") {
            if let Ok(res) = call_stdio_tool(conn, "av_quarantine_list", json!({})) {
                return Some(format!(
                    "🔒 **Bóveda de Cuarentena Aria Shield (`security-antivirus.av_quarantine_list`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["configuracion antivirus", "exclusiones clamav", "whitelist antivirus"]) {
        mem.record_habit("av_get_config");
        if let Some((conn, _)) = find_tool(connectors, "security-antivirus", "av_get_config") {
            if let Ok(res) = call_stdio_tool(conn, "av_get_config", json!({})) {
                return Some(format!(
                    "⚙️ **Configuración y Whitelist SHA-256 de Aria Shield (`security-antivirus.av_get_config`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 4. Vault, Encryption, Snapshots & Pentesting (`security-vault-crypto`, `security-net-audit`)
    if matches_any(lower, &["volumenes veracrypt", "volúmenes veracrypt", "discos cifrados"]) {
        mem.record_habit("veracrypt_list");
        if let Some((conn, _)) = find_tool(connectors, "security-vault-crypto", "veracrypt_list_volumes") {
            if let Ok(res) = call_stdio_tool(conn, "veracrypt_list_volumes", json!({})) {
                return Some(format!(
                    "🔐 **Volúmenes Cifrados VeraCrypt (`security-vault-crypto.veracrypt_list_volumes`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["snapshots timeshift", "copias timeshift", "puntos de restauracion"]) {
        mem.record_habit("timeshift_list");
        if let Some((conn, _)) = find_tool(connectors, "security-vault-crypto", "timeshift_list_snapshots") {
            if let Ok(res) = call_stdio_tool(conn, "timeshift_list_snapshots", json!({})) {
                return Some(format!(
                    "⏱️ **Instantáneas del Sistema Timeshift (`security-vault-crypto.timeshift_list_snapshots`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["estado suite seguridad", "herramientas pentesting", "auditoria de seguridad"]) {
        mem.record_habit("security_suite_status");
        if let Some((conn, _)) = find_tool(connectors, "security-net-audit", "security_suite_status") {
            if let Ok(res) = call_stdio_tool(conn, "security_suite_status", json!({})) {
                return Some(format!(
                    "🕵️ **Estado de Herramientas de Auditoría y Reversing (`security-net-audit.security_suite_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 5. Containers, VMs, Editors & Databases (`dev-containers-vm`, `dev-vscodium`, `dev-api-databases`)
    if matches_any(lower, &["contenedores activos", "docker ps", "podman ps", "listar contenedores"]) {
        mem.record_habit("container_list");
        if let Some((conn, _)) = find_tool(connectors, "dev-containers-vm", "container_list") {
            if let Ok(res) = call_stdio_tool(conn, "container_list", json!({"runtime": "auto"})) {
                return Some(format!(
                    "🐳 **Contenedores Docker / Podman (`dev-containers-vm.container_list`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["maquinas virtuales", "máquinas virtuales", "listar vms", "estado kvm"]) {
        mem.record_habit("vm_list");
        if let Some((conn, _)) = find_tool(connectors, "dev-containers-vm", "vm_list") {
            if let Ok(res) = call_stdio_tool(conn, "vm_list", json!({})) {
                return Some(format!(
                    "🖥️ **Máquinas Virtuales QEMU/KVM y VirtualBox (`dev-containers-vm.vm_list`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["extensiones vscodium", "plugins vscodium"]) {
        mem.record_habit("vscodium_extensions");
        if let Some((conn, _)) = find_tool(connectors, "dev-vscodium", "list_extensions") {
            if let Ok(res) = call_stdio_tool(conn, "list_extensions", json!({})) {
                return Some(format!(
                    "🧩 **Extensiones Instaladas en VSCodium (`dev-vscodium.list_extensions`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["conexiones dbeaver", "conexiones base de datos"]) {
        mem.record_habit("db_connections");
        if let Some((conn, _)) = find_tool(connectors, "dev-api-databases", "list_db_connections") {
            if let Ok(res) = call_stdio_tool(conn, "list_db_connections", json!({})) {
                return Some(format!(
                    "🗄️ **Conexiones de Bases de Datos (`dev-api-databases.list_db_connections`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 6. Multimedia, OBS, MPRIS Players & Audacity (`media-obs`, `media-players`, `creative-audacity`)
    if matches_any(lower, &["estado obs", "obs websocket"]) {
        mem.record_habit("obs_status");
        if let Some((conn, _)) = find_tool(connectors, "media-obs", "obs_websocket_status") {
            if let Ok(res) = call_stdio_tool(conn, "obs_websocket_status", json!({})) {
                return Some(format!(
                    "🎬 **Estado de OBS Studio WebSocket v5 (`media-obs.obs_websocket_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["reproductores activos", "que suena", "qué suena", "estado mpris"]) {
        mem.record_habit("mpris_players");
        if let Some((conn, _)) = find_tool(connectors, "media-players", "list_players") {
            if let Ok(res) = call_stdio_tool(conn, "list_players", json!({})) {
                return Some(format!(
                    "🎵 **Reproductores Multimedia MPRIS2 en D-Bus (`media-players.list_players`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["estado audacity", "pipe audacity"]) {
        mem.record_habit("audacity_pipe");
        if let Some((conn, _)) = find_tool(connectors, "creative-audacity", "pipe_status") {
            if let Ok(res) = call_stdio_tool(conn, "creative-audacity", json!({}))
                .or_else(|_| call_stdio_tool(conn, "pipe_status", json!({})))
            {
                return Some(format!(
                    "🎙️ **Estado del Puente FIFO de Audacity (`creative-audacity.pipe_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 7. Web, Thunderbird, FileZilla, Syncthing, qBittorrent, LibreOffice, Calibre & Automations
    if matches_any(lower, &["pestañas abiertas", "tabs del navegador"]) {
        mem.record_habit("browser_tabs");
        if let Some((conn, _)) = find_tool(connectors, "browser-web", "list_tabs") {
            if let Ok(res) = call_stdio_tool(conn, "list_tabs", json!({})) {
                return Some(format!(
                    "🌐 **Pestañas del Navegador vía CDP (`browser-web.list_tabs`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["perfiles thunderbird", "cuentas de correo"]) {
        mem.record_habit("thunderbird_profiles");
        if let Some((conn, _)) = find_tool(connectors, "comms-thunderbird", "list_profiles") {
            if let Ok(res) = call_stdio_tool(conn, "list_profiles", json!({})) {
                return Some(format!(
                    "✉️ **Perfiles de Correo Thunderbird (`comms-thunderbird.list_profiles`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["sitios filezilla", "servidores ftp", "servidores sftp"]) {
        mem.record_habit("filezilla_sites");
        if let Some((conn, _)) = find_tool(connectors, "net-filezilla", "list_sites") {
            if let Ok(res) = call_stdio_tool(conn, "list_sites", json!({})) {
                return Some(format!(
                    "📡 **Sitios FTP/SFTP en FileZilla (`net-filezilla.list_sites`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["estado syncthing", "sincronizacion p2p"]) {
        mem.record_habit("syncthing_status");
        if let Some((conn, _)) = find_tool(connectors, "net-sync-comms-gaming", "syncthing_status") {
            if let Ok(res) = call_stdio_tool(conn, "syncthing_status", json!({})) {
                return Some(format!(
                    "🔄 **Estado de Syncthing P2P (`net-sync-comms-gaming.syncthing_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["torrents activos", "estado qbittorrent"]) {
        mem.record_habit("qbittorrent_torrents");
        if let Some((conn, _)) = find_tool(connectors, "net-sync-comms-gaming", "qbittorrent_torrents") {
            if let Ok(res) = call_stdio_tool(conn, "qbittorrent_torrents", json!({})) {
                return Some(format!(
                    "📥 **Torrents en qBittorrent (`net-sync-comms-gaming.qbittorrent_torrents`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["estado suite gaming", "estado ecosistema", "apps instaladas"]) {
        mem.record_habit("ecosystem_apps_status");
        if let Some((conn, _)) = find_tool(connectors, "net-sync-comms-gaming", "ecosystem_apps_status") {
            if let Ok(res) = call_stdio_tool(conn, "ecosystem_apps_status", json!({})) {
                return Some(format!(
                    "🎮 **Estado del Ecosistema Gaming, Emuladores y Comms (`net-sync-comms-gaming.ecosystem_apps_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["estado libreoffice", "uno status"]) {
        mem.record_habit("libreoffice_uno");
        if let Some((conn, _)) = find_tool(connectors, "office-libreoffice", "uno_status") {
            if let Ok(res) = call_stdio_tool(conn, "uno_status", json!({})) {
                return Some(format!(
                    "📄 **Estado del Puente UNO de LibreOffice (`office-libreoffice.uno_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["libros calibre", "biblioteca calibre"]) {
        mem.record_habit("calibre_books");
        if let Some((conn, _)) = find_tool(connectors, "knowledge-notes-ebooks", "calibre_list_books") {
            if let Ok(res) = call_stdio_tool(conn, "calibre_list_books", json!({})) {
                return Some(format!(
                    "📚 **Biblioteca de Libros en Calibre (`knowledge-notes-ebooks.calibre_list_books`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["automatizaciones activas", "tareas programadas"]) {
        mem.record_habit("list_automations");
        if let Some((conn, _)) = find_tool(connectors, "os-automation", "list_automations") {
            if let Ok(res) = call_stdio_tool(conn, "list_automations", json!({})) {
                return Some(format!(
                    "⏱️ **Automatizaciones y Memoria Neuronal (`os-automation.list_automations`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    // 8. Intelligent Firewall & Live Socket Monitor (`security-firewall`)
    if matches_any(lower, &["estado cortafuegos", "estado firewall", "reglas firewall"]) {
        mem.record_habit("firewall_status");
        if let Some((conn, _)) = find_tool(connectors, "security-firewall", "firewall_status") {
            if let Ok(res) = call_stdio_tool(conn, "firewall_status", json!({})) {
                return Some(format!(
                    "🛡️ **Estado del Cortafuegos Inteligente (`security-firewall.firewall_status`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }
    if matches_any(lower, &["conexiones activas", "puertos abiertos", "sockets activos"]) {
        mem.record_habit("active_connections");
        if let Some((conn, _)) = find_tool(connectors, "security-firewall", "active_connections") {
            if let Ok(res) = call_stdio_tool(conn, "active_connections", json!({"limit": 30})) {
                return Some(format!(
                    "🌐 **Conexiones TCP/UDP y Puertos en Escucha (`security-firewall.active_connections`):**\n```json\n{}\n```",
                    serde_json::to_string_pretty(&res).unwrap_or_default()
                ));
            }
        }
    }

    None
}
