# AI Subsystem & Daemon (`aria-daemon`)

`aria-daemon` (written in Rust under `core/daemon/`) **is the OS-level brain of AriaOS**. Running natively as a `systemd` system service (`root`), it spans every layer—from the Linux kernel and hardware telemetry (`os-kernel`) through system services and ClamAV quarantine (`/var/lib/ariaos/quarantine`) all the way up to KDE Plasma desktop applications (`os-files` / Dolphin) bridged seamlessly into the active graphical user session via `core/sdk/python/aria_sdk/session.py`.

## Multi-Layer OS Bridge (`core/sdk/python/aria_sdk/session.py`)

Because `aria-daemon` operates at kernel/OS privilege while user applications live in a KDE Plasma Wayland/XDG session:
- **Trash & User Files**: `os-files` resolves the owner of the target path (or active desktop user via `/run/user/<uid>`) and writes FreeDesktop `.trashinfo` items directly into the user's Dolphin Trash (`~aria/.local/share/Trash`) with aligned ownership.
- **Desktop Launchers**: GUI actions such as `open_in_dolphin` inspect active Plasma/KWin process environments (`WAYLAND_DISPLAY`, `DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, `XDG_RUNTIME_DIR`) and spawn into the desktop session UID cleanly.
- **OS Quarantine Vault**: `security-antivirus` stores isolated samples in `/var/lib/ariaos/quarantine` (`0700 root:root`, payloads `0400`) so untrusted user programs cannot read or execute quarantined malware, while Dolphin right-click actions (`ariaos-av-scan`) communicate directly with `aria-daemon` over `/run/ariaos/agent.sock`.

## How a Request Flows

1. **Connector Discovery (`core/daemon/src/manifest.rs`)**:
   At startup, `aria-daemon` scans (first match wins per connector ID, skipping directories prefixed with `_`):
   - `$ARIAOS_CONNECTORS_DIR` (if set)
   - `./connectors`
   - `$HOME/.config/ariaos/connectors`
   - `/usr/lib/ariaos/connectors`
2. **Daemon IPC Server (`core/daemon/src/server.rs`)**:
   When launched as `aria-daemon` or `aria-daemon serve`, it binds a newline-delimited JSON Unix socket:
   - `$ARIAOS_SOCKET_PATH` (if set)
   - `/run/ariaos/agent.sock` (when `/run/ariaos` exists via `systemd RuntimeDirectory=ariaos`)
   - `/tmp/ariaos-agent.sock` (fallback)
   Socket permissions are set to `0666` so desktop user sessions can communicate with the system service cleanly.
3. **LLM Tool-Calling Loop (`core/daemon/src/ollama.rs`)**:
   - Sends tool JSON schemas for all discovered `stdio` connectors to Ollama `/api/chat` with `num_ctx: 8192`.
   - Default model is `qwen2.5:3b` (override via `--model` or `ARIAOS_MODEL`).
   - System prompt instructs the model to chain read-only tools autonomously without asking unnecessarily and summarize observed data directly.
4. **Connector Execution (`core/daemon/src/rpc.rs`)**:
   Spawns the connector entrypoint (e.g., `python3 connector.py`) inside the connector's root directory, sends a single JSON-RPC 2.0 `tools/call` request over `stdin`, and reads the JSON response from `stdout`.

## CLI Subcommands

```bash
aria-daemon serve [--model <name>]               # Start Unix socket daemon
aria-daemon list                                 # List discovered connectors and tools
aria-daemon call <connector> <tool> [json_args]  # Execute a single tool directly
aria-daemon ask "<prompt>" [--model <name>]      # Single natural-language turn via Ollama
aria-daemon chat [--model <name>]                # Interactive terminal session
```

## Unix Socket IPC Protocol

Requests are single-line JSON objects sent to `/run/ariaos/agent.sock`:

- `{"action": "list_tools"}` -> returns registered connectors and tool schemas.
- `{"action": "ask", "prompt": "...", "approved_tools": ["<connector>.<tool>"]}` -> runs an Ollama turn across all OS layers; executes `read` tools autonomously and returns `requires_confirmation: true` + `pending_call` whenever a `write` or `privileged` action requires explicit user approval from the Command Bar.
- `{"action": "call", "connector": "...", "tool": "...", "arguments": {...}, "approved": false}` -> executes a specific tool directly; returns `requires_confirmation: true` for `write`/`privileged` tools when `approved` is `false`.
