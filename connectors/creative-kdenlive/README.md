# `creative-kdenlive` Connector

**Target Programs:** `Kdenlive` & MLT framework (`melt`).

## Control API
- **Primary Bridge:** `.kdenlive` MLT XML project inspection + **`melt`** headless rendering + Kdenlive D-Bus actions (`org.kde.kdenlive*`).
- **Planned Tools:**
  - `inspect_project` (`read`): Read timeline clips, duration, resolution, and render profiles.
  - `render_timeline` (`write`): Trigger background MLT/Kdenlive renders to a target output path.
