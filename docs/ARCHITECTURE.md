# AriaOS Architecture

> **Core principle:** In AriaOS, the AI is **not** a user-space chat window bolted onto an OS. It is an OS-native subsystem (`systemd` service + D-Bus interface + standardized connector bus) capable of inspecting state, organizing files, and driving applications through structured APIs.

---

## 1. High-Level System Layers

```
+-------------------------------------------------------------------+
|  User Interfaces                                                  |
|  - ariaOS-Command-Bar (global shortcut, Wayland/KDE overlay)      |
|  - CLI (`aria` client) / Voice / Desktop Widgets                  |
+---------------------------------+---------------------------------+
                                  |  Unix Socket / D-Bus (org.ariaos.Agent1)
                                  v
+-------------------------------------------------------------------+
|  core/daemon (`aria-daemon` - Rust, systemd service)              |
|  - Intent & Tool Router (Ollama / local LLM tool-calling)         |
|  - Connector Registry (auto-discovers `connectors/*/manifest.json`)
|  - Policy & Permission Broker (read / write / privileged + Polkit)|
|  - Action Audit & Undo Journal                                    |
+--------+------------------------+------------------------+--------+
         | Tier 1                 | Tier 2                 | Tier 3
         v                        v                        v
+-----------------+    +--------------------+    +------------------+
| Native OS IPC   |    | Program Connectors |    | UI Fallback      |
| (D-Bus/systemd) |    | (JSON-RPC / MCP)   |    | (Wayland/AT-SPI2)|
| - KDE / KWin    |    | - LibreOffice UNO  |    | - Only when app  |
| - systemd units |    | - Blender Python   |    |   lacks API/CLI  |
| - NetworkMgr    |    | - OBS WebSocket    |    |                  |
| - PipeWire      |    | - FFmpeg / Git /   |    |                  |
| - Polkit        |    |   Browser CDP      |    |                  |
+-----------------+    +--------------------+    +------------------+
```

---

## 2. Three-Tier Control Model (Reaching 100% of Programs)

To control every tool and application on the PC reliably—without brittle screen-scraping as the primary path—AriaOS uses a strict priority order:

1. **Tier 1 — Native OS & Desktop IPC (`D-Bus`, `systemd`, sockets)**
   - Window management, virtual desktops, notifications, clipboard, audio routing (`PipeWire`), networking (`NetworkManager`), power, and service health (`systemd`) are controlled directly over D-Bus.
2. **Tier 2 — Standardized Program Connectors (`connectors/<name>/`)**
   - Every supported program or subsystem exposes its capabilities through a self-contained connector directory containing a `manifest.json` and an executable adapter (written in Rust, Python, Go, or shell) speaking **JSON-RPC 2.0 (MCP-compatible)** over `stdio` or a local Unix socket.
   - Examples:
     - **File & PC Hygiene (`os-files`, `os-system`)**: smart organization, duplicate detection, disk cleanup, safe quarantine/trash, service diagnostics.
     - **Productivity & Media**: LibreOffice (UNO API), Blender (`bpy`), OBS Studio (WebSocket API), FFmpeg & ImageMagick, Brave/Firefox (CDP / Native Messaging), VSCodium, Git.
3. **Tier 3 — Universal Accessibility / UI Fallback (`os-desktop` / AT-SPI2)**
   - Reserved exclusively for legacy or closed-source GUI applications that expose neither an API, socket, nor CLI.

---

## 3. Why This Structure Scales

Adding support for a new program never requires modifying the core daemon:

1. Create a folder under `connectors/<program-name>/` from `connectors/_template/`.
2. Declare its tools, JSON Schema arguments, and risk levels in `manifest.json`.
3. Implement the adapter using `core/sdk/python` (or any language speaking the JSON-RPC contract in `core/protocol/`).
4. `aria-daemon` automatically discovers the manifest, registers its tools with the local LLM, and enforces permissions.

---

## 4. Safety, Trust Tiers, and PC Maintenance

Because the agent can control the entire OS and filesystem, every tool in `manifest.json` must declare a `risk_level`:

| Risk Level | Scope | Default Execution Policy |
| :--- | :--- | :--- |
| `read` | Inspect files, list windows, read logs, check disk/CPU/RAM | Automatic (no prompt) |
| `write` | Organize/move/rename files, convert media, open/control apps | Policy-controlled + reversible via undo journal / Trash |
| `privileged` | Delete permanently, format/partition, modify `/etc`, `pacman`, `systemd` | Explicit confirmation in `ariaOS-Command-Bar` + Polkit auth |

---

## 5. Repository Layout

```
AriaOS/
├── core/
│   ├── daemon/          # Compiled Rust OS daemon (`aria-daemon`)
│   ├── protocol/        # Connector manifest JSON Schema & JSON-RPC spec
│   └── sdk/python/      # Lightweight Python SDK for building connectors fast
├── connectors/          # Modular program & OS adapters (1 folder = 1 tool/app; see connectors/README.md)
│   ├── _template/       # Copy-paste starter for new connectors
│   ├── os-files/        # File organization, search & safe cleanup
│   ├── os-system/       # System health, systemd & process inspection
│   ├── os-desktop/      # KDE Plasma / KWin / D-Bus desktop control
│   ├── multimedia-ffmpeg/
│   ├── office-*/        # LibreOffice, Okular
│   ├── browser-web/     # Brave / Firefox CDP & Native Messaging
│   ├── media-*/         # OBS Studio, VLC / Elisa
│   ├── creative-*/      # GIMP, Krita, Blender, Audacity, Kdenlive
│   └── dev-*/           # VSCodium / Kate, Git / gh
├── packages/            # Arch PKGBUILDs, ariaOS-Theme & app integration patches
│   ├── ariaos-core/
│   ├── ariaos-command-bar/
│   ├── ariaos-theme/
│   └── ariaos-app-integrations/
├── ui/
│   └── command-bar/     # Global KDE/Wayland floating command bar spec
├── os/
│   ├── archiso/         # Arch Linux live/install ISO profile & systemd units
│   └── scripts/         # Reproducible ISO build scripts
├── docs/                # Architecture & developer guides
└── tests/               # Protocol, manifest & connector verification tests
```

