# Security & Trust Tiers

AriaOS enforces strict capability boundaries so local AI autonomy never leads to silent destructive actions or credential leaks.

## Tool Risk Classification

Every tool in `manifest.json` must declare `risk_level` and `reversible` (validated against `core/protocol/connector.schema.json`):

| `risk_level` | Intent | Default Daemon Socket Behavior | CLI / Interactive Behavior |
| :--- | :--- | :--- | :--- |
| **`read`** | Inspection, search, status queries | Allowed automatically | Allowed automatically |
| **`write`** | Non-destructive creation, file organization, launching apps, playback control | Blocked unless UI sends `"approved": true` after confirmation | Prompts `[y/N]` unless `--yes` |
| **`privileged`** | System service restarts, package installs, network scans (`nmap`), VM power control | Blocked unless UI sends `"approved": true` after confirmation | Always prompts `[y/N]` |

## Policy Modes (`core/daemon/src/policy.rs`)

- **`ApprovalMode::ReadOnly`**: Used by default for background `ask` requests over the Unix socket; permits `read` tools and rejects `write` / `privileged`.
- **`ApprovalMode::Interactive`**: Used by `aria-daemon chat` and `aria-daemon call`; prompts `[y/N]` on terminal stderr for mutating/privileged actions.
- **`ApprovalMode::AutoWrite`**: Enabled via `--yes` CLI flag; permits `write` automatically while still prompting for `privileged`.

## Audit Trail

Every tool execution (or confirmation denial) is appended as a JSON line to `/tmp/ariaos-audit.jsonl` (configurable via `ARIAOS_AUDIT_LOG`), recording:
- Unix timestamp (`ts`)
- `connector` ID and `tool` name
- `risk_level`
- `status` (`ok`, `error`, `denied`, `confirmation_required`)
- `arguments`

## Connector-Level Hardening

- **No silent overwrites**: File-producing connectors (`office-libreoffice`, `multimedia-ffmpeg`, `os-storage`, `creative-krita`, `creative-blender`, `creative-kdenlive`, `creative-design-photo`, `creative-video-transcode`, `knowledge-notes-ebooks`) explicitly refuse to overwrite existing output paths.
- **No secret leakage**: `net-filezilla` redacts saved passwords from `sitemanager.xml`, `dev-api-databases` strips credentials from DBeaver/MySQL Workbench config reads, and `security-vault-crypto` only checks `.kdbx` headers without unlocking databases.
- **Strict input validation**: Hostnames, systemd unit names, MPRIS2 service names, URL schemes (`http`/`https` only), and vault paths (path traversal checks) are validated before any binary execution or IPC call.
