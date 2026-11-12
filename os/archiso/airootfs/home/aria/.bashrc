# AriaOS Cyber Obsidian — Interactive Bash Configuration
[[ $- != *i* ]] && return

export EDITOR="kate"
export VISUAL="kate"
export HISTCONTROL=ignoreboth:erasedups
export HISTSIZE=5000

# Cyber Obsidian Neon Cyan Prompt
PS1='\[\e[1;36m\]⚡ aria@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\]\[\e[1;36m\] ❯\[\e[0m\] '

# Fast AriaOS CLI Shortcuts
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias grep='grep --color=auto'
alias optimize='aria-daemon optimize'
alias heal='aria-daemon heal'
alias hud='aria-command-bar &'
alias monitor='ariaos-monitor &'
alias store='ariaos-store &'
alias firewall='ariaos-firewall &'
alias snapshots='ariaos-snapshots &'
alias vault='ariaos-vault &'
alias aistudio='ariaos-ai-studio &'
alias netradar='ariaos-netradar &'
alias optimizer='ariaos-optimizer &'
alias clipboard='ariaos-clipboard &'

# Display compact Cyber Obsidian status header on interactive terminal launch
if [ -z "${ARIAOS_BANNER_SHOWN:-}" ]; then
  export ARIAOS_BANNER_SHOWN=1
  echo -e "\e[1;36m╭──────────────────────────────────────────────────────────────────────────╮\e[0m"
  echo -e "\e[1;36m│\e[0m  ⚡ \e[1;37mARIA OS // CYBER OBSIDIAN\e[0m — \e[0;36mKernel Neural Core Activo (<0.5 ms)\e[0m      \e[1;36m│\e[0m"
  echo -e "\e[1;36m│\e[0m  💡 Comandos: \e[1;32maria \"estado del sistema\"\e[0m | \e[1;32maria \"optimizar ram\"\e[0m | \e[1;32mheal\e[0m   \e[1;36m│\e[0m"
  echo -e "\e[1;36m╰──────────────────────────────────────────────────────────────────────────╯\e[0m"
fi
