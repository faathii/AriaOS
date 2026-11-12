# `dev-vscodium` Connector

**Target Programs:** `VSCodium` & `Kate`.

## Control API
- **Primary Bridge:** `codium` / `kate` CLI + local companion extension bridge over Unix socket for workspace-aware file/terminal/task actions.
- **Planned Tools:**
  - `list_open_workspaces` (`read`): Inspect active project folders and open files.
  - `open_in_editor` (`write`): Open a file/line or workspace directly in VSCodium or Kate.
