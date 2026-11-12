"""AriaOS Internationalization (i18n) & Central AI Configuration Manager.

Provides multilingual dictionary support across:
- Spanish (es - default)
- English (en)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Simplified Chinese (zh)
- Japanese (ja)

Also manages ~/.config/ariaos/config.json with safe system fallbacks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "es": "Español",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "zh": "中文 (简体)",
    "ja": "日本語",
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "es",
    "model": "qwen2.5:3b",
    "ollama_url": "http://127.0.0.1:11434",
    "num_ctx": 8192,
    "temperature": 0.3,
    "approval_mode": "interactive",  # interactive, autowrite, readonly
    "hotkey": "Alt+Space",
    "enabled_connector_groups": {
        "core_os": True,
        "security": True,
        "development": True,
        "creative": True,
        "office": True,
        "browser": True,
        "comms_gaming": True,
    },
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # --- Common & Navigation ---
    "settings_title": {
        "es": "Configuración de la IA de AriaOS",
        "en": "AriaOS AI Settings",
        "fr": "Paramètres IA d'AriaOS",
        "de": "AriaOS KI-Einstellungen",
        "it": "Impostazioni IA di AriaOS",
        "pt": "Configurações de IA do AriaOS",
        "zh": "AriaOS 人工智能设置",
        "ja": "AriaOS AI 設定",
    },
    "tab_general": {
        "es": "General e Idioma",
        "en": "General & Language",
        "fr": "Général & Langue",
        "de": "Allgemein & Sprache",
        "it": "Generale e Lingua",
        "pt": "Geral e Idioma",
        "zh": "常规与语言",
        "ja": "一般と言語",
    },
    "tab_model": {
        "es": "Modelo e Inferencia",
        "en": "Model & Inference",
        "fr": "Modèle & Inférence",
        "de": "Modell & Inferenz",
        "it": "Modello e Inferenza",
        "pt": "Modelo e Inferência",
        "zh": "模型与推理",
        "ja": "モデルと推論",
    },
    "tab_security": {
        "es": "Seguridad y Autonomía",
        "en": "Security & Autonomy",
        "fr": "Sécurité & Autonomie",
        "de": "Sicherheit & Autonomie",
        "it": "Sicurezza e Autonomia",
        "pt": "Segurança e Autonomia",
        "zh": "安全与自主权",
        "ja": "セキュリティと自律性",
    },
    "tab_audit": {
        "es": "Auditoría y Privacidad",
        "en": "Audit & Privacy",
        "fr": "Audit & Confidentialité",
        "de": "Audit & Datenschutz",
        "it": "Audit e Privacy",
        "pt": "Auditoria e Privacidade",
        "zh": "审计与隐私",
        "ja": "監査とプライバシー",
    },
    "btn_save": {
        "es": "Guardar y Aplicar",
        "en": "Save & Apply",
        "fr": "Enregistrer & Appliquer",
        "de": "Speichern & Anwenden",
        "it": "Salva e Applica",
        "pt": "Salvar e Aplicar",
        "zh": "保存并应用",
        "ja": "保存して適用",
    },
    "btn_cancel": {
        "es": "Cancelar",
        "en": "Cancel",
        "fr": "Annuler",
        "de": "Abbrechen",
        "it": "Annulla",
        "pt": "Cancelar",
        "zh": "取消",
        "ja": "キャンセル",
    },
    "btn_close": {
        "es": "Cerrar",
        "en": "Close",
        "fr": "Fermer",
        "de": "Schließen",
        "it": "Chiudi",
        "pt": "Fechar",
        "zh": "关闭",
        "ja": "閉じる",
    },
    "saved_success": {
        "es": "Configuración guardada correctamente.",
        "en": "Settings saved successfully.",
        "fr": "Paramètres enregistrés avec succès.",
        "de": "Einstellungen erfolgreich gespeichert.",
        "it": "Impostazioni salvate con successo.",
        "pt": "Configurações salvas com sucesso.",
        "zh": "设置已成功保存。",
        "ja": "設定が正常に保存されました。",
    },

    # --- Language Tab ---
    "language_label": {
        "es": "Idioma principal de la IA y del sistema:",
        "en": "Primary AI and system language:",
        "fr": "Langue principale de l'IA et du système :",
        "de": "Hauptsprache der KI und des Systems:",
        "it": "Lingua principale dell'IA e del sistema:",
        "pt": "Idioma principal da IA e do sistema:",
        "zh": "人工智能和系统的主语言：",
        "ja": "AIおよびシステムの主要言語：",
    },
    "hotkey_label": {
        "es": "Atajo global para abrir la Barra IA:",
        "en": "Global hotkey to open AI Command Bar:",
        "fr": "Raccourci global pour ouvrir la barre IA :",
        "de": "Globaler Hotkey zum Öffnen der KI-Befehlsleiste:",
        "it": "Scorciatoia globale per la barra IA:",
        "pt": "Atalho global para abrir a barra de IA:",
        "zh": "打开 AI 命令栏的全局快捷键：",
        "ja": "AI コマンドバーを開くグローバルホットキー：",
    },
    "autostart_label": {
        "es": "Iniciar demonio aria-daemon en el arranque del sistema",
        "en": "Start aria-daemon service on system boot",
        "fr": "Démarrer le service aria-daemon au démarrage du système",
        "de": "aria-daemon-Dienst beim Systemstart ausführen",
        "it": "Avvia il servizio aria-daemon all'avvio del sistema",
        "pt": "Iniciar o serviço aria-daemon na inicialização do sistema",
        "zh": "在系统启动时启动 aria-daemon 服务",
        "ja": "システム起動時に aria-daemon サービスを開始",
    },

    # --- Model Tab ---
    "ollama_url_label": {
        "es": "Punto de enlace de Ollama (local o red):",
        "en": "Ollama API endpoint (local or network):",
        "fr": "Point de terminaison Ollama (local ou réseau) :",
        "de": "Ollama API-Endpunkt (lokal oder Netzwerk):",
        "it": "Endpoint API di Ollama (locale o di rete):",
        "pt": "Ponto de extremidade do Ollama (local ou rede):",
        "zh": "Ollama API 端点（本地或网络）：",
        "ja": "Ollama API エンドポイント（ローカルまたはネットワーク）：",
    },
    "model_select_label": {
        "es": "Modelo local predeterminado:",
        "en": "Default local AI model:",
        "fr": "Modèle d'IA local par défaut :",
        "de": "Standardmäßiges lokales KI-Modell:",
        "it": "Modello IA locale predefinito:",
        "pt": "Modelo de IA local padrão:",
        "zh": "默认本地 AI 模型：",
        "ja": "デフォルトのローカル AI モデル：",
    },
    "btn_test_ollama": {
        "es": "Probar conexión y listar modelos",
        "en": "Test connection & list models",
        "fr": "Tester la connexion & lister les modèles",
        "de": "Verbindung testen & Modelle auflisten",
        "it": "Testa connessione e lista modelli",
        "pt": "Testar conexão e listar modelos",
        "zh": "测试连接并列出模型",
        "ja": "接続をテストしてモデルを一覧表示",
    },
    "btn_pull_model": {
        "es": "Descargar modelo seleccionado (ollama pull)",
        "en": "Download selected model (ollama pull)",
        "fr": "Télécharger le modèle sélectionné (ollama pull)",
        "de": "Ausgewähltes Modell herunterladen (ollama pull)",
        "it": "Scarica il modello selezionato (ollama pull)",
        "pt": "Baixar modelo selecionado (ollama pull)",
        "zh": "下载选定的模型 (ollama pull)",
        "ja": "選択したモデルをダウンロード (ollama pull)",
    },
    "context_size_label": {
        "es": "Ventana de contexto (tokens):",
        "en": "Context window size (tokens):",
        "fr": "Taille de la fenêtre de contexte (tokens) :",
        "de": "Kontextfenstergröße (Tokens):",
        "it": "Dimensione della finestra di contesto (token):",
        "pt": "Tamanho da janela de contexto (tokens):",
        "zh": "上下文窗口大小 (tokens)：",
        "ja": "コンテキストウィンドウサイズ (トークン)：",
    },
    "temperature_label": {
        "es": "Temperatura de respuesta (0.0 precisa -> 1.0 creativa):",
        "en": "Response temperature (0.0 precise -> 1.0 creative):",
        "fr": "Température de réponse (0.0 précis -> 1.0 créatif) :",
        "de": "Antworttemperatur (0.0 präzise -> 1.0 kreativ):",
        "it": "Temperatura di risposta (0.0 precisa -> 1.0 creativa):",
        "pt": "Temperatura de resposta (0.0 precisa -> 1.0 criativa):",
        "zh": "生成温度 (0.0 精确 -> 1.0 创意)：",
        "ja": "応答温度 (0.0 正確 -> 1.0 創造的)：",
    },

    # --- Security Tab ---
    "approval_mode_label": {
        "es": "Nivel de supervisión y autonomía de la IA:",
        "en": "AI supervision & autonomy policy:",
        "fr": "Politique de supervision et autonomie de l'IA :",
        "de": "Überwachungs- und Autonomierichtlinie der KI:",
        "it": "Criteri di supervisione e autonomia dell'IA:",
        "pt": "Política de supervisão e autonomia da IA:",
        "zh": "人工智能监督与自主权策略：",
        "ja": "AI の監視と自律性ポリシー：",
    },
    "mode_interactive": {
        "es": "Interactivo (Recomendado): Preguntar antes de modificar archivos o el sistema",
        "en": "Interactive (Recommended): Ask before modifying files or system state",
        "fr": "Interactif (Recommandé) : Demander avant de modifier des fichiers ou le système",
        "de": "Interaktiv (Empfohlen): Vor Änderungen an Dateien oder System nachfragen",
        "it": "Interattivo (Consigliato): Chiedi prima di modificare file o sistema",
        "pt": "Interativo (Recomendado): Perguntar antes de alterar arquivos ou o sistema",
        "zh": "交互模式（推荐）：在修改文件或系统状态之前进行询问确认",
        "ja": "対話型（推奨）：ファイルやシステムを変更する前に確認を求める",
    },
    "mode_autowrite": {
        "es": "Autónomo moderado: Aplicar escrituras seguras; confirmar solo acciones de kernel/root",
        "en": "Moderate Autonomous: Auto-approve safe writes; confirm root/kernel actions only",
        "fr": "Autonome modéré : Écritures sûres automatiques ; confirmer root/noyau uniquement",
        "de": "Moderat autonom: Sichere Schreibvorgänge automatisch; nur Root/Kernel bestätigen",
        "it": "Autonomo moderato: Scritture sicure automatiche; conferma solo azioni root/kernel",
        "pt": "Autônomo moderado: Gravações seguras automáticas; confirmar apenas ações root/kernel",
        "zh": "适度自主：自动执行安全写入；仅确认 root/内核 级关键操作",
        "ja": "適度な自律：安全な書き込みを自動承認；root/カーネル 操作のみ確認",
    },
    "mode_readonly": {
        "es": "Solo Lectura: La IA solo puede inspeccionar y diagnosticar, nunca modificar",
        "en": "Read-Only: AI can only inspect and diagnose, never modify state",
        "fr": "Lecture seule : L'IA peut uniquement inspecter et diagnostiquer, jamais modifier",
        "de": "Schreibgeschützt: Die KI kann nur prüfen und diagnostizieren, nichts ändern",
        "it": "Sola lettura: L'IA può solo ispezionare e diagnosticare, mai modificare",
        "pt": "Somente leitura: A IA só pode inspecionar e diagnosticar, nunca modificar",
        "zh": "只读模式：人工智能只能检查和诊断，绝不修改任何内容",
        "ja": "読み取り専用：AI は検査と診断のみ行い、変更は一切行いません",
    },
    "connector_groups_label": {
        "es": "Grupos de conectores habilitados en el sistema:",
        "en": "Enabled connector domain groups in system:",
        "fr": "Groupes de connecteurs activés dans le système :",
        "de": "Aktivierte Konnektoren-Gruppen im System:",
        "it": "Gruppi di connettori abilitati nel sistema:",
        "pt": "Grupos de conectores habilitados no sistema:",
        "zh": "系统中启用的连接器功能组：",
        "ja": "システムで有効なコネクタグループ：",
    },

    # --- Audit Tab ---
    "audit_title": {
        "es": "Registro de acciones y llamadas a herramientas:",
        "en": "Tool calls and action audit log:",
        "fr": "Journal des appels d'outils et actions :",
        "de": "Protokoll der Werkzeugaufrufe und Aktionen:",
        "it": "Registro delle chiamate agli strumenti e azioni:",
        "pt": "Registro de chamadas de ferramentas e ações:",
        "zh": "工具调用与操作审计日志：",
        "ja": "ツール呼び出しとアクションの監査ログ：",
    },
    "btn_clear_audit": {
        "es": "Vaciar registro de auditoría",
        "en": "Clear audit log",
        "fr": "Effacer le journal d'audit",
        "de": "Audit-Protokoll löschen",
        "it": "Cancella registro audit",
        "pt": "Limpar registro de auditoria",
        "zh": "清空审计日志",
        "ja": "監査ログを消去",
    },

    # --- Command Bar & Prompt Strings ---
    "cmd_placeholder": {
        "es": "Pregunta a AriaOS en tu idioma, o escribe /tools o /call <conector> <tool>...",
        "en": "Ask AriaOS anything in your language, or type /tools or /call <connector> <tool>...",
        "fr": "Demandez à AriaOS dans votre langue, ou tapez /tools ou /call...",
        "de": "Frage AriaOS in deiner Sprache oder tippe /tools oder /call...",
        "it": "Chiedi ad AriaOS nella tua lingua, o digita /tools o /call...",
        "pt": "Pergunte ao AriaOS no seu idioma ou digite /tools ou /call...",
        "zh": "用您的语言向 AriaOS 提问，或输入 /tools 或 /call...",
        "ja": "お好みの言語で AriaOS に質問するか、/tools や /call と入力...",
    },
    "permission_request_title": {
        "es": "Solicitud de Permiso de AriaOS",
        "en": "AriaOS Permission Request",
        "fr": "Demande d'autorisation AriaOS",
        "de": "AriaOS Berechtigungsanfrage",
        "it": "Richiesta di autorizzazione AriaOS",
        "pt": "Pedido de permissão do AriaOS",
        "zh": "AriaOS 权限请求",
        "ja": "AriaOS 権限リクエスト",
    },
    "permission_approve_prompt": {
        "es": "¿Aprobar acción {risk}?\n\nHerramienta: {tool}\nArgumentos: {args}",
        "en": "Approve {risk} action?\n\nTool: {tool}\nArguments: {args}",
        "fr": "Approuver l'action {risk} ?\n\nOutil : {tool}\nArguments : {args}",
        "de": "{risk}-Aktion genehmigen?\n\nWerkzeug: {tool}\nArgumente: {args}",
        "it": "Approvare l'azione {risk}?\n\nStrumento: {tool}\nArgomenti: {args}",
        "pt": "Aprovar ação {risk}?\n\nFerramenta: {tool}\nArgumentos: {args}",
        "zh": "批准 {risk} 操作？\n\n工具：{tool}\n参数：{args}",
        "ja": "{risk} アクションを承認しますか？\n\nツール：{tool}\n引数：{args}",
    },
}


def resolve_config_path(custom_path: Path | str | None = None) -> Path:
    if custom_path:
        return Path(custom_path).expanduser()
    custom = os.environ.get("ARIAOS_CONFIG_PATH")
    if custom:
        return Path(custom).expanduser()
    home_cfg = Path.home() / ".config" / "ariaos" / "config.json"
    if home_cfg.exists():
        return home_cfg
    sys_cfg = Path("/etc/ariaos/config.json")
    if sys_cfg.exists():
        return sys_cfg
    return home_cfg


def load_ariaos_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    p = resolve_config_path(config_path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
                # Merge nested enabled_connector_groups safely
                if isinstance(data.get("enabled_connector_groups"), dict):
                    merged_groups = dict(DEFAULT_CONFIG["enabled_connector_groups"])
                    merged_groups.update(data["enabled_connector_groups"])
                    cfg["enabled_connector_groups"] = merged_groups
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_ariaos_config(new_config: Dict[str, Any], config_path: Path | str | None = None) -> Path:
    cfg = load_ariaos_config(config_path)
    cfg.update(new_config)
    p = resolve_config_path(config_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def get_current_language() -> str:
    cfg = load_ariaos_config()
    lang = str(cfg.get("language") or "").strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    # Fallback to system env
    for var in ("LC_ALL", "LANG"):
        val = os.environ.get(var, "").lower()
        prefix = val.split("_")[0].split(".")[0]
        if prefix in SUPPORTED_LANGUAGES:
            return prefix
    return "es"


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    target_lang = lang or get_current_language()
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    template = entry.get(target_lang) or entry.get("en") or entry.get("es") or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
