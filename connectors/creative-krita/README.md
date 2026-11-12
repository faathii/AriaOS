# `creative-krita` Connector

**Target Programs:** `Krita` (digital painting & 2D animation).

## Control API
- **Primary Bridge:** Krita **Python Scripting API (`krita`)** plugin exposing a local Unix socket + `.kra` archive inspection.
- **Planned Tools:**
  - `inspect_kra` (`read`): Inspect canvas size, layer tree, and animation frames.
  - `export_document` / `run_krita_action` (`write`): Export layers/spritesheets or trigger Krita actions.
