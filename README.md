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

An Open and Free Community: A strictly collaborative development model under the GPL v3 license, ensuring that the software remains free, open, and accessible to everyone—forever. 🏛️ Core System Architecture
The internal structure of ariaOS is divided into modular layers to ensure performance, low resource consumption, and stability:

The Kernel (Kernel & Arch Base): A hyper-optimized, lightweight rolling-release system with support for hardware acceleration (GPU/VRAM).

The Native Inference Engine (systemd-ai): A background service that starts with the operating system, keeping the language model instantly available via a local socket.

The Shell and Control Layer (APIs / D-Bus): A native communication bridge that allows the AI ​​to interact with the operating system through secure commands and direct calls, rather than relying on slow mouse emulations.

The AI ​​User Interface: A universal floating command bar (triggered by global keyboard shortcuts) for conversing with the system and executing actions seamlessly.

🧰 Pre-installed Software (Complete Ecosystem)
To ensure ariaOS is fully functional from the very first boot, the ISO includes a carefully curated suite of dual-use tools (manageable by humans and controllable by the AI):
Desktop Environment: KDE Plasma (elegant, customizable, and lightweight) / XFCE (maximum resource efficiency).
Office Suite: LibreOffice (word processor and spreadsheets).
Web Browsing: Firefox / Brave.
Multimedia and Graphics: Lightweight viewers, media players, and integrated command-line tools such as ImageMagick and FFmpeg.
Search and File Tools: Rapid indexing utilities (ripgrep, fd, fzf) for ultra-efficient data management.

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
