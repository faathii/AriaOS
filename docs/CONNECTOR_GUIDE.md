# How to Add a New Program Connector

AriaOS is designed so anyone can add support for a new application or system tool without touching `core/daemon`.

## 1. Copy the Template

Copy `connectors/_template/` to `connectors/<your-tool>/`:

- Naming convention: `<category>-<program>` (for example: `office-libreoffice`, `creative-blender`, `browser-brave`, `dev-git`, `os-audio`).

## 2. Define `manifest.json`

Every connector **must** include a valid `manifest.json` matching `core/protocol/connector.schema.json`:

- `id`: unique lowercase identifier (e.g., `"creative-blender"`).
- `name` & `version`: human-readable name and SemVer string.
- `tier`: `"os_ipc"`, `"program_api"`, or `"ui_fallback"`.
- `transport`: `"stdio"` (default, spawned on demand) or `"unix_socket"`.
- `entrypoint`: command array executed by `aria-daemon` (e.g., `["python3", "connector.py"]`).
- `tools`: array of tools exposed to the AI, each with:
  - `name`: action name (snake_case, e.g., `render_scene`).
  - `description`: concise explanation so the LLM knows when to call it.
  - `risk_level`: `"read"`, `"write"`, or `"privileged"`.
  - `input_schema`: JSON Schema object defining parameters.

## 3. Implement the Adapter

If writing in Python, use `aria_sdk.ConnectorServer` from `core/sdk/python`:

```python
from aria_sdk import ConnectorServer

server = ConnectorServer("my-connector", "0.1.0")

@server.tool("ping")
def handle_ping(params: dict) -> dict:
    return {"status": "ok", "echo": params.get("message", "")}

if __name__ == "__main__":
    server.run_stdio()
```

You can also write connectors in **Rust**, **Go**, **C++**, or **Bash**—the only requirement is reading newline-delimited JSON-RPC 2.0 requests from `stdin` (or Unix socket) and writing JSON-RPC 2.0 responses to `stdout`.

## 4. Validate and Test

Run the repository test suite to verify your `manifest.json` schema and JSON-RPC handshake:

```bash
python -m unittest discover -s tests -v
```

