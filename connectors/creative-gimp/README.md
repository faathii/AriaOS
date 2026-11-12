# `creative-gimp` Connector

**Target Programs:** `GIMP` (GNU Image Manipulation Program).

## Control API
- **Primary Bridge:** GIMP batch / **Script-Fu & Python-Fu** (`gimp -i -b ...`) + local plugin RPC socket for live open-canvas operations.
- **Planned Tools:**
  - `inspect_xcf` (`read`): Read layers, dimensions, and color profile of `.xcf`/image projects.
  - `batch_edit_image` (`write`): Resize, crop, color-correct, remove background, or export to PNG/WebP without overwriting the original.
