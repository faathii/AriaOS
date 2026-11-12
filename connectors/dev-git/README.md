# `dev-git` Connector

**Target Programs:** `git` & GitHub CLI (`gh`).

## Control API
- **Primary Bridge:** Direct `git` and `gh` CLI execution returning structured JSON/status.
- **Planned Tools:**
  - `repo_status` / `repo_diff` / `repo_log` (`read`): Inspect repository status, branch, uncommitted diffs, and recent commits.
  - `stage_and_commit` (`write`): Stage files and create a commit with confirmation.
  - `push_or_create_pr` (`privileged`): Push branches or open PRs via `gh` only with explicit approval.
