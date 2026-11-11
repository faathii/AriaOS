"""Template connector for integrating a new program into AriaOS."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# Allow running directly from the repo without an editable pip install.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="template-example", version="0.1.0")


@server.tool("ping")
def ping(args: Dict[str, Any]) -> Dict[str, Any]:
    """Simple health-check tool."""
    message = str(args.get("message", "pong"))
    return {"reply": message}


if __name__ == "__main__":
    server.run_stdio()

