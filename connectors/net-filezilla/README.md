# `net-filezilla` Connector

**Target Programs:** `FileZilla` & standard `sftp`/`lftp` CLI tools.

## Control API
- **Primary Bridge:** FileZilla site profiles (`~/.config/filezilla/sitemanager.xml` read-only lookup) + `sftp`/`lftp` structured transfer execution.
- **Planned Tools:**
  - `list_saved_sites` / `list_remote_dir` (`read`): Inspect configured sites and remote directory listings.
  - `transfer_files` (`write` / `privileged`): Upload or download files safely with dry-run preview.
