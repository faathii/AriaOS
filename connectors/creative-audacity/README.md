# `creative-audacity` Connector

**Target Programs:** `Audacity` (multi-track audio editor).

## Control API
- **Primary Bridge:** Audacity **`mod-script-pipe`** named-pipe API (`/tmp/audacity_script_pipe.*`) for programmatic project and effect control.
- **Planned Tools:**
  - `get_project_info` (`read`): Inspect open tracks, sample rate, and selection state.
  - `apply_audio_effect` / `export_audio` (`write`): Normalize, denoise, trim, or export audio tracks.
