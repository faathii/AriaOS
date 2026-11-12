# AI Subsystem & Daemon (`aria-daemon`)

`aria-daemon` (written in Rust under `core/daemon/`) is the core system broker that connects user prompts, local LLM inference (Ollama), security policies, and all external connectors.

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
- `{"action": "ask", "prompt": "..."}` -> runs an Ollama turn in `ReadOnly` mode.
- `{"action": "call", "connector": "...", "tool": "...", "arguments": {...}, "approved": false}` -> executes a specific tool directly; returns `requires_confirmation: true` for `write`/`privileged` tools when `approved` is `false`.
