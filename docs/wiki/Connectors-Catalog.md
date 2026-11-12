# Connectors Catalog

AriaOS currently ships **30 active connectors** under `connectors/`. All connectors use zero-dependency Python 3 + `aria_sdk` over `stdio` JSON-RPC 2.0.

## System & OS Core

| Connector ID | Target Stack / API | Tools |
| :--- | :--- | :--- |
| `os-kernel` | Linux Kernel (`/proc`, `/sys`, `dmesg`, `sysctl`, `modprobe`, `lspci`/`lsusb`/`ip`) | `kernel_telemetry`, `dmesg_inspect`, `hardware_pci_usb`, `sysctl_read`, `sysctl_write`, `kernel_module_manage` |
| `os-files` | KDE Dolphin / XDG Trash / `fd` / `rg` / SHA-256 | `scan_directory`, `search_files`, `file_info`, `find_duplicates`, `organize_directory`, `move_to_trash`, `open_in_dolphin` |
| `os-system` | `systemd`, `/proc`, `journalctl`, KInfoCenter | `system_health_summary`, `list_top_processes`, `service_status`, `restart_service` |
| `os-desktop` | KDE Plasma, `notify-send`, `gtk-launch`/`kioclient` | `desktop_environment_info`, `send_notification`, `launch_application` |
| `os-packages` | `pacman`, `checkupdates`, `paccache` | `list_installed_packages`, `search_packages`, `check_system_updates`, `clean_package_cache`, `install_package` |
| `os-storage` | `lsblk`, `zipfile`, `tarfile` | `list_block_devices`, `inspect_archive`, `create_archive`, `extract_archive` |

## Office, Web & Communications

| Connector ID | Target Programs / API | Tools |
| :--- | :--- | :--- |
| `office-libreoffice` | LibreOffice (`soffice --headless`, UNO TCP, ODF/OOXML XML) | `inspect_document`, `convert_document`, `uno_status` |
| `office-okular` | Okular + Poppler (`pdfinfo`, `pdftotext`) | `inspect_pdf`, `extract_pdf_text`, `open_document` |
| `browser-web` | Brave (CDP HTTP `:9222`, Bookmarks JSON) & Firefox | `list_tabs`, `search_bookmarks`, `open_url` |
| `comms-thunderbird` | Thunderbird (`profiles.ini`, Gloda SQLite RO, `-compose`) | `list_profiles`, `search_messages`, `compose_email` |
| `net-filezilla` | FileZilla (`sitemanager.xml` redacted) & `sftp` | `list_sites`, `list_remote_dir` |

## Media, Creative, Photo & Video

| Connector ID | Target Programs / API | Tools |
| :--- | :--- | :--- |
| `multimedia-ffmpeg` | FFmpeg (`ffprobe`, `ffmpeg`) & ImageMagick | `inspect_media`, `convert_media` |
| `media-players` | VLC, Elisa, Spotify via MPRIS2 D-Bus (`qdbus6`/`gdbus`) | `list_players`, `get_playback_status`, `control_playback`, `play_media` |
| `media-obs` | OBS Studio (native WebSocket v5 + SHA-256 auth) & Kamoso | `obs_websocket_status`, `obs_request`, `launch_capture_app` |
| `creative-gimp` | GIMP (`Script-Fu` batch, PNG/JPEG/GIF/BMP/XCF headers) | `inspect_image`, `run_script_fu` |
| `creative-krita` | Krita (`.kra` ZIP/XML layer parser + `--export` CLI) | `inspect_krita_doc`, `export_krita` |
| `creative-blender` | Blender (`bpy` background script & frame render) | `inspect_blend_scene`, `render_frame` |
| `creative-audacity` | Audacity (`mod-script-pipe` FIFO IPC) | `pipe_status`, `send_pipe_command` |
| `creative-kdenlive` | Kdenlive & MLT (`melt`, `.kdenlive` XML inspector) | `inspect_project`, `render_project` |
| `creative-design-photo` | Inkscape (SVG XML + export), Darktable, RawTherapee | `inspect_svg`, `inkscape_export`, `darktable_export`, `rawtherapee_export` |
| `creative-video-transcode` | HandBrakeCLI, Shotcut (`.mlt`), Pitivi (`.xges`) | `inspect_video_project`, `handbrake_transcode`, `launch_video_app` |

## Knowledge, Security, Dev, Containers & Gaming

| Connector ID | Target Programs / API | Tools |
| :--- | :--- | :--- |
| `knowledge-notes-ebooks` | Obsidian Vaults (Markdown), Calibre (`calibredb`, `ebook-convert`) | `search_obsidian_vault`, `create_obsidian_note`, `calibre_list_books`, `calibre_convert_ebook` |
| `security-antivirus` | ClamAV (`clamdscan`, `clamscan`, `freshclam`, Quarantine Vault) | `av_status`, `av_scan_path`, `av_update_signatures`, `av_quarantine_list`, `av_quarantine_file`, `av_restore_file` |
| `security-vault-crypto` | KeePassXC (`.kdbx`), VeraCrypt, Timeshift, Flameshot | `keepassxc_check_db`, `veracrypt_list_volumes`, `timeshift_list_snapshots`, `flameshot_capture` |
| `security-net-audit` | Wireshark (`tshark`), Ghidra/Cutter/rizin, Nmap, Burp, Metasploit, Hashcat, John | `security_suite_status`, `inspect_binary`, `inspect_pcap`, `nmap_scan` |
| `dev-git` | Git CLI (`git status`, `log`, `diff`, `commit`) | `repo_status`, `repo_log`, `repo_diff`, `stage_and_commit` |
| `dev-vscodium` | VSCodium (`codium`) & Kate CLI | `list_extensions`, `open_in_editor` |
| `dev-containers-vm` | Docker, Podman, Portainer, VirtualBox (`VBoxManage`), QEMU/KVM (`virsh`) | `container_list`, `container_logs`, `vm_list`, `vm_power` |
| `dev-api-databases` | DBeaver, MySQL Workbench, Postman, Insomnia, HTTP preview | `http_get_preview`, `list_db_connections`, `launch_dev_client` |
| `net-sync-comms-gaming` | Syncthing REST, qBittorrent API, Steam, Heroic, Lutris, RetroArch, PCSX2, RPCS3, DuckStation, Telegram, Element, Signal, Discord, Spotify, Stremio, FreeTube, Ventoy, Stacer | `ecosystem_apps_status`, `syncthing_status`, `qbittorrent_torrents`, `launch_ecosystem_app` |

## Installing Expanded App Suites

To install any optional suite onto an installed AriaOS system:

```bash
ariaos-install-apps --creative --security --dev --gaming --comms
ariaos-install-apps --all          # Includes official/multilib + AUR via yay
ariaos-install-apps --portainer    # Deploys Portainer CE on Docker (:9443)
```
