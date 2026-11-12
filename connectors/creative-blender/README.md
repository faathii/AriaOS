# `creative-blender` Connector

**Target Programs:** `Blender` (3D modeling, animation, rendering).

## Control API
- **Primary Bridge:** Blender **`bpy` Python API** (`blender --background --python ...` and optional live add-on RPC socket inside Blender).
- **Planned Tools:**
  - `inspect_blend_scene` (`read`): List objects, cameras, materials, frame range, and render engine in a `.blend` file.
  - `render_scene` / `run_bpy_script` (`write`): Render frames/animations or automate scene setup cleanly.
