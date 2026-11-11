# `ariaOS-Command-Bar`

Global floating command bar for KDE Plasma (Wayland layer-shell / Qt/QML), invoked via a global keyboard shortcut (e.g. `Meta+Space`).

## Responsibilities

1. **Direct OS Entry Point**: Connects to `aria-daemon` over `/run/ariaos/agent.sock` and `org.ariaos.Agent1` (D-Bus).
2. **Live Tool Transparency**: Displays which connector (`os-files`, `os-system`, `os-desktop`, etc.) and tool are running in real time.
3. **Interactive Permission Prompts**: Renders clear approve/cancel dialogs whenever a tool declares `risk_level: "privileged"` or requires user review before mutating files.

