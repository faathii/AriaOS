# Developer SDK & Protocol

Every AriaOS capability lives in a self-contained directory under `connectors/<id>/` with at least two files:
- `manifest.json` — strictly validated against `core/protocol/connector.schema.json`.
- `connector.py` — executable Python 3 JSON-RPC 2.0 server using `core/sdk/python/aria_sdk`.

## Manifest Schema Rules (`connector.schema.json`)

- `additionalProperties` is `false` on both the root object and every `tools[]` item.
- `id`: `^[a-z0-9][a-z0-9-]*$` (must match directory name).
- `version`: SemVer `X.Y.Z`.
- `tier`: `"os_ipc" | "program_api" | "ui_fallback"`.
- `transport`: `"stdio" | "unix_socket" | "dbus"` (`stdio` is exposed to Ollama tool calling).
- Each tool requires `name` (`^[a-z][a-z0-9_]*$`), `description` (keep concise for the 8192-token context budget), `risk_level` (`read` / `write` / `privileged`), `reversible` (boolean), and `input_schema` (`type: "object"`).

## Python SDK Pattern (`aria_sdk`)

```python
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer

server = ConnectorServer("my-connector", "0.1.0")

@server.tool("my_tool")
def my_tool(params: dict) -> dict:
    value = params.get("value")
    if not isinstance(value, str) or not value.strip():
        raise ConnectorError("'value' must be a non-empty string.", -32602)
    return {"echo": value.strip()}

if __name__ == "__main__":
    server.run_stdio()
```

### Important Implementation Guidelines

1. **Validate inputs (`-32602`) before probing OS binaries (`-32000`)** so unit tests pass cleanly across Windows dev machines and Linux VMs.
2. **Use Python Standard Library only** inside connectors so they run immediately in minimal Arch installations without external `pip` dependencies.
3. **Never overwrite output files** silently — fail with `-32602` if the target file already exists.

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```
