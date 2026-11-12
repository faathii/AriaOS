# `media-players` Connector

**Target Programs:** `VLC Media Player`, `Elisa`, `Kaffeine`.

## Control API
- **Primary Bridge:** Standard Linux **MPRIS2 D-Bus** interface (`org.mpris.MediaPlayer2.*`) + VLC RC/HTTP interface when needed.
- **Planned Tools:**
  - `get_playback_status` (`read`): Read current track/video title, artist, position, and playback state.
  - `control_playback` (`write`): Play, pause, next/previous track, seek, or adjust player volume.
  - `play_media` (`write`): Open a file or playlist in VLC or Elisa.
