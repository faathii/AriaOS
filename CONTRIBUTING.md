# Contributing to AriaOS

Thank you for helping build **AriaOS**! Because AriaOS embeds an AI agent directly into the operating system, we prioritize **speed, modularity, and safety**.

## Ways to Contribute

1. **Add a Program Connector (`connectors/`)**: Follow [docs/CONNECTOR_GUIDE.md](docs/CONNECTOR_GUIDE.md) to integrate a new application via its native API, IPC, or CLI.
2. **Core Daemon (`core/daemon`)**: Improve the Rust broker, Ollama/LLM tool-calling loop, D-Bus bridge, or undo journal.
3. **ArchISO & Packaging (`os/archiso`)**: Help refine packages, KDE Plasma defaults, `systemd` services, and GPU acceleration setup.
4. **Command Bar UI (`ui/command-bar`)**: Design and build the floating KDE/Wayland interface.

## Safety & Code Standards

- **Never bypass `risk_level`**: Any tool that mutates user data must declare `"write"`; any destructive or system-wide operation (`rm`, disk partitioning, `pacman`, `systemd` unit changes) must declare `"privileged"`.
- **Prefer reversible actions**: File cleanup and organization tools should default to dry-run previews and move files to Trash/quarantine rather than permanently deleting them.
- **Keep connectors isolated**: Do not couple app-specific logic into `core/daemon`.
- **Run tests before opening a PR**:

```bash
python -m unittest discover -s tests -v
```

## License

All contributions are licensed under the **GNU General Public License v3.0 (GPL v3)**. See [LICENSE](LICENSE).

