# `os-system` Connector

Tier 1 (`os_ipc`) connector bridging `aria-daemon` to `systemd`, hardware telemetry (`/proc`, `sysfs`), and `pacman` queries over D-Bus (`org.freedesktop.systemd1`).

Privileged mutations (restarting units, installing/removing packages) require `risk_level: "privileged"` confirmation + Polkit authorization.

