#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="ariaos"
iso_label="ARIAOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="AriaOS Community <https://github.com/faathii/AriaOS>"
iso_application="AriaOS Live/Install Media"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="arch"
bootmodes=('bios.syslinux'
           'uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/sudoers.d/10-wheel"]="0:0:440"
  ["/home/aria"]="1000:1000:755"
  ["/home/aria/Desktop"]="1000:1000:755"
  ["/home/aria/Desktop/ariaos-command-bar.desktop"]="1000:1000:755"
  ["/home/aria/Desktop/ariaos-installer.desktop"]="1000:1000:755"
  ["/home/aria/Desktop/ariaos-welcome.desktop"]="1000:1000:755"
  ["/home/aria/.config"]="1000:1000:755"
  ["/home/aria/.config/dolphinrc"]="1000:1000:644"
  ["/home/aria/.config/kglobalshortcutsrc"]="1000:1000:644"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/usr/bin/aria-command-bar"]="0:0:755"
  ["/usr/bin/aria-daemon"]="0:0:755"
  ["/usr/bin/ariaos-apply-branding"]="0:0:755"
  ["/usr/bin/ariaos-av-scan"]="0:0:755"
  ["/usr/bin/ariaos-clamav-sync"]="0:0:755"
  ["/usr/bin/ariaos-file-action"]="0:0:755"
  ["/usr/bin/ariaos-install-apps"]="0:0:755"
  ["/usr/bin/ariaos-onboarding"]="0:0:755"
  ["/usr/bin/ariaos-welcome"]="0:0:755"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
)
