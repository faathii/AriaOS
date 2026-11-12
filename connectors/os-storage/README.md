# `os-storage` Connector

**Target Programs:** `Ark`, `lsblk`, `smartctl`, `GParted` (inspection / partitioned safely).

## Control API
- **Read (`risk=read`)**: List block devices, mountpoints, filesystem types, SMART disk health, and inspect archive contents (`.zip`, `.tar.gz`, `.7z`, `.rar`) via `bsdtar`/`7z`.
- **Write (`risk=write`)**: Compress or extract archives cleanly into dedicated subdirectories via `Ark` / `7z` / `tar`.
- **Privileged (`risk=privileged`)**: Mount/unmount external drives or run partition tools (`GParted`/filesystem checks) only after explicit user confirmation.

