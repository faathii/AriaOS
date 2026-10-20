# AriaOS
AriaOS is a minimalist distribution based on Arch Linux that integrates a local AI agent. It combines the power and speed of Arch with intelligent automation, allowing you to control your system and applications using natural language—quickly, fluidly, and entirely autonomously.

🚀 What is ariaOS?
ariaOS was created with a clear premise: to break down the barriers between the user, traditional software, and artificial intelligence. It is not merely an assistant running on top of a conventional operating system; rather, it is a cutting-edge Linux distribution where AI is woven into the very fabric of the OS—featuring native permissions, local APIs, and a complete, ready-to-use ecosystem from the very first moment.

Inspired by the power, minimalism, and philosophy of Arch Linux, ariaOS aims to provide the "all-inclusive" convenience of major commercial operating systems—complete with an office suite, web browser, multimedia tools, and pre-configured drivers—while supercharging the experience with a local inference engine and intelligent tools that eliminate repetitive tasks.

🎯 Project Vision and Objectives
The long-term goal of ariaOS is to redefine how we interact with our personal computers:

Local Sovereignty and Privacy: All AI processing runs locally on your hardware via optimized engines (such as Ollama), ensuring that your data never leaves your device.

A True Hybrid Ecosystem: A system where users can interact with their graphical environment in the traditional way—using windows, a mouse, and familiar applications—or invoke the AI ​​to execute complex workflows seamlessly in the background.

Zero-Friction Installation: A self-contained ISO image that comes pre-loaded with the inference engine, optimized models, and productivity applications, eliminating the cumbersome manual setup typically required for local AI.

An Open and Free Community: A strictly collaborative development model under the GPL v3 license, ensuring that the software remains free, open, and accessible to everyone—forever. 
🏛️ Core System Architecture
The internal structure of ariaOS is divided into modular layers to ensure performance, low resource consumption, and stability:

The Kernel (Kernel & Arch Base): A hyper-optimized, lightweight rolling-release system with support for hardware acceleration (GPU/VRAM).

The Native Inference Engine (systemd-ai): A background service that starts with the operating system, keeping the language model instantly available via a local socket.

The Shell and Control Layer (APIs / D-Bus): A native communication bridge that allows the AI ​​to interact with the operating system through secure commands and direct calls, rather than relying on slow mouse emulations.

The AI ​​User Interface: A universal floating command bar (triggered by global keyboard shortcuts) for conversing with the system and executing actions seamlessly.

🧰 Pre-installed Software (Complete Ecosystem) on ariaOS
1. Desktop Environment and Customization
KDE Plasma: The primary graphical environment—highly customizable, fluid, and featuring an integrated manager for add-ons and widgets.

KDE Discover & Pacman/AUR Helper (Pamac or Yay): Graphical software centers and package management tools for installing any additional application with a single click.

ariaOS-Theme: An exclusive, pre-configured visual package (includes Breeze Dark icons, custom color schemes, and optimized typography).

2. Office, Reading, and Productivity
LibreOffice Suite Complete: Includes a word processor (Writer), spreadsheets (Calc), presentations (Impress), and databases (Base).

Okular: A universal document viewer (supports PDF, EPUB, comics, annotations, and digital signatures).

Thunderbird: The most powerful and widely used email, calendar, and contact management client on Linux.

KCalc: An advanced calculator (supporting scientific and various numeral systems).

3. Browsing, Networking, and Connectivity
Brave Browser (Default) / Firefox: Secure, privacy-focused web browsers with built-in tracker blockers and synchronization features.

FileZilla: A standard FTP, FTPS, and SFTP client for advanced server and remote file management.

Kamoso / OBS Studio: Tools for screen recording, streaming, and webcam management.

Kaffeine / VLC Media Player: The ultimate multimedia players, capable of handling virtually any existing audio or video codec.

Elisa: A fast, minimalist local audio player.

4. Creation, Design, and Advanced Multimedia
GIMP: The definitive open-source image editor and retouching tool (a true alternative to Photoshop).

Krita: Professional software for digital painting, illustration, and 2D animation.

Blender: The global standard for 3D modeling, animation, rendering, and sculpting. Audacity: Digital audio multi-track editor and recorder.

Kdenlive: Professional-grade non-linear, multi-camera video editor.

5. Utilities, Compression, and System
Dolphin: The official KDE file manager (featuring tab support, split-screen view, and an integrated terminal).

Ark: A universal file compression manager (compatible with formats such as .zip, .rar, .7z, .tar.gz, etc.).

Kate: An advanced text editor with syntax highlighting, designed for software development and technical note-taking.

GParted: The official graphical hard drive partition editor.

BleachBit: A system cleaning tool used to free up disk space and remove temporary files or obsolete cache data.

KInfoCenter / Hardinfo: Tools for detailed hardware diagnostics and performance monitoring.

6. Development, Terminal, and Essential Tools (Linux Staples)
Konsole: KDE’s advanced terminal emulator—fast, tab-enabled, and featuring customizable profiles.

Git & GitHub CLI (gh): Industry-standard tools for version control and repository management, included by default.

Visual Studio Code (VSCodium—the open-source version): The world’s most popular integrated development environment (IDE), ready for programming.

High-performance CLI utilities: ripgrep (rg), fd, fzf, tmux, and htop/btop for real-time resource monitoring.

7. AI Layer and Native Automation (ariaOS-Core)
Ollama (Local Background Server): An optimized inference engine running natively via system services (systemd).

Integrated Multimodal/Base Language Model: An optimized model pre-downloaded within the ISO to ensure offline functionality.

ariaOS-Command-Bar: A universal, floating graphical interface (triggered via keyboard shortcut) connected to the operating system and applications through internal APIs. ImageMagick & FFmpeg: Command-line multimedia automation that allows AI to process images and video, invisibly and upon user request.

🗺️ Roadmap
[ ] Phase 1: Initial repository setup and ISO build scripts using archiso. [ ] Phase 2: Stabilization of the Arch Linux base system and packaging of the desktop environment and essential software.
[ ] Phase 3: Integration of the local inference daemon and deployment of the base model within the image.
[ ] Phase 4: Development of the floating command bar and system automation connectors.
[ ] Phase 5: Testing in virtual environments (QEMU/VirtualBox) and release of the first public Alpha version.

🤝 How to Contribute?
ariaOS is a community project open to all developers, designers, and enthusiasts of Linux and AI!
Fork the repository.
Explore the "Issues" section to find tasks labeled "good first issue" or "help wanted."
Submit your pull requests containing improvements, automation scripts, or fixes.
Join project discussions to propose new architectural ideas.

📄 License
This project is distributed under the terms of the GNU General Public License v3.0 (GPL v3). See the LICENSE file for more details.
