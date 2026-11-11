# Building the AriaOS Arch Linux ISO

Because `archiso`, `pacman`, and `devtools` (`pkgctl`) run natively on Arch Linux, builds are performed inside an Arch Linux environment (such as the `AriaOS-Builder` VirtualBox VM).

## 1. Install Build Tools inside Arch Linux

```bash
sudo pacman -Syu --needed archiso devtools base-devel rust git
```

- **`archiso`** (`mkarchiso`): Builds the bootable AriaOS ISO from `os/archiso/`.
- **`devtools`** (`pkgctl`): Downloads and modifies official Arch Linux package sources (`PKGBUILD`) when customizing system packages or the kernel.
- **`rust`**: Compiles `core/daemon` (`aria-daemon`).

## 2. Access the Repository from VirtualBox

With the `AriaOS` VirtualBox shared folder configured (`C:\Users\hamza\Desktop\AriaOS`):

```bash
sudo mkdir -p /mnt/ariaos
sudo mount -t vboxsf AriaOS /mnt/ariaos
cd /mnt/ariaos
```

## 3. Build the ISO

```bash
./os/scripts/build-iso.sh
```

The resulting ISO will be placed in `os/archiso/out/` (git-ignored).

