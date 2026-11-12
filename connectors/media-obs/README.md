# `media-obs` Connector

**Target Programs:** `OBS Studio` & `Kamoso`.

## Control API
- **Primary Bridge:** **OBS WebSocket v5 API** (`ws://127.0.0.1:4455`) for deterministic control of scenes, sources, recording, and streaming.
- **Planned Tools:**
  - `get_obs_status` / `list_scenes` (`read`): Query active scene, recording/streaming state, and audio levels.
  - `switch_scene` / `start_recording` / `stop_recording` (`write`): Control recording and scene transitions.
  - `start_streaming` (`privileged`): Require explicit confirmation before going live.
