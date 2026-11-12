# Command Bar Guide (`ariaOS-Command-Bar`)

The **AriaOS Command Bar** (`ui/command-bar/`) is the floating desktop entry point for KDE Plasma 6, bound globally to **`Alt+Space`**.

## Components

- **`ui/command-bar/aria_ipc.py`**: Zero-dependency Python Unix socket client (`AriaDaemonClient`) and command parser (`parse_command`).
- **`ui/command-bar/aria_command_bar.py`**: Floating frameless PyQt6 command palette (`AriaCommandBar`) with background worker threads (`QThread`), live tool listing, interactive permission dialogs, and terminal `--cli` / `--prompt` fallback.
- **`ui/command-bar/ariaos-command-bar.desktop`**: XDG desktop entry launched by `/usr/bin/aria-command-bar`.
- **Global Shortcut**: Pre-registered in `/etc/skel/.config/kglobalshortcutsrc` and `/home/aria/.config/kglobalshortcutsrc` (`_launch=Alt+Space,none,Launch AriaOS Command Bar`).

## Command Modes

1. **Natural Language (`ask`)**:
   Type any request directly (e.g., *"Check CPU, RAM, failed services, and list active Docker containers"*). Sent to `aria-daemon` -> Ollama -> autonomous read-tool chaining.
2. **Direct Tool Listing (`/tools`)**:
   Queries `{"action": "list_tools"}` from `aria-daemon` and populates clickable tool templates inside the palette.
3. **Deterministic Tool Call (`/call`)**:
   Syntax:
   ```text
   /call <connector> <tool> [json_arguments]
   ```
   Example:
   ```text
   /call os-files scan_directory {"path": "/home/aria/Downloads"}
   ```
   If the tool has `risk_level: "write"` or `"privileged"`, `aria-daemon` returns `requires_confirmation: true` and the Command Bar opens a confirmation dialog displaying the exact tool and JSON arguments before re-submitting with `approved: true`.

## CLI & Diagnostic Usage

```bash
# Verify imports & installation
aria-command-bar --check

# Run a single command in terminal
aria-command-bar --prompt "/tools"

# Run in interactive terminal mode (no GUI required)
aria-command-bar --cli
```
