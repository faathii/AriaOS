# `ariaOS-Command-Bar`

Global floating command bar for KDE Plasma 6 (`PyQt6`), invoked via a global keyboard shortcut (`Alt+Space` by default in AriaOS KDE shortcuts).

## Files

- `aria_ipc.py`: Pure-stdlib Unix socket client (`AriaDaemonClient`) and slash-command parser (`/tools`, `/call`, natural-language `ask`).
- `aria_command_bar.py`: Floating Qt6 command bar UI (`aria-command-bar`) with async execution, tool suggestions, interactive `write`/`privileged` confirmation prompts, and `--cli` fallback.
- `ariaos-command-bar.desktop`: XDG desktop entry registered with KDE global shortcuts.

## Usage

```bash
# Graphical floating bar (KDE Plasma)
python3 ui/command-bar/aria_command_bar.py

# Single prompt in terminal / headless test
python3 ui/command-bar/aria_command_bar.py --prompt "/tools"
```
