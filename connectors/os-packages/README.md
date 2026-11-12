# `os-packages` Connector

**Target Programs:** `pacman`, `yay` / `pamac`, KDE Discover, `paccache`, `BleachBit`.

## Control API
- **Read (`risk=read`)**: Query installed packages (`pacman -Q`), search repositories (`pacman -Ss`), inspect available updates (`checkupdates`), and estimate cleanable package/cache space.
- **Write (`risk=write`)**: Clean old package caches safely (`paccache -rk2`) or clean user-selected temp caches.
- **Privileged (`risk=privileged`)**: Install, upgrade, or remove system packages (`pacman -S` / `pacman -Rns`), always requiring explicit user confirmation + Polkit.
