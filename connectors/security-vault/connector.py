"""AriaOS `security-vault` connector: Cryptographic Vault, SSH Key Auditor & CSPRNG Generator."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="security-vault", version="0.1.0")


def _vault_path() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    p = Path(home) / ".local" / "share" / "ariaos" / "vault_store.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _master_key() -> bytes:
    seed = os.environ.get("ARIAOS_VAULT_KEY", "ariaos-cyber-obsidian-kernel-vault-v1")
    return hashlib.pbkdf2_hmac("sha256", seed.encode("utf-8"), b"ariaos-salt-x86_64", 100_000, dklen=32)


def _encrypt(plaintext: str) -> str:
    key = _master_key()
    nonce = secrets.token_bytes(16)
    pt_bytes = plaintext.encode("utf-8")
    stream = bytearray()
    counter = 0
    while len(stream) < len(pt_bytes):
        block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    ct = bytes(a ^ b for a, b in zip(pt_bytes, stream[: len(pt_bytes)]))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(nonce + tag + ct).decode("ascii")


def _decrypt(token: str) -> str:
    key = _master_key()
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, tag, ct = raw[:16], raw[16:32], raw[32:]
    expected_tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Vault integrity check failed (HMAC mismatch)")
    stream = bytearray()
    counter = 0
    while len(stream) < len(ct):
        block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    pt = bytes(a ^ b for a, b in zip(ct, stream[: len(ct)]))
    return pt.decode("utf-8")


def _load_vault() -> List[Dict[str, Any]]:
    path = _vault_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    default_items = [
        {
            "label": "AriaOS Kernel Telemetry Token",
            "category": "api_token",
            "ciphertext": _encrypt("aria-kcore-9f8e7d6c5b4a3210-obsidian"),
            "updated_at": int(time.time()),
        }
    ]
    try:
        path.write_text(json.dumps(default_items, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return default_items


def _save_vault(items: List[Dict[str, Any]]) -> None:
    try:
        _vault_path().write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise ConnectorError(f"Failed to save vault store: {exc}", code=-32000)


def _audit_ssh_keys() -> List[Dict[str, Any]]:
    home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp")
    ssh_dir = home / ".ssh"
    results: List[Dict[str, Any]] = []
    if not ssh_dir.exists():
        return results
    for f in sorted(ssh_dir.iterdir()):
        if f.is_file() and not f.name.endswith(".pub") and f.name not in {"known_hosts", "config", "authorized_keys"}:
            mode = oct(f.stat().st_mode & 0o777)
            secure = mode in {"0o600", "0o400"} or os.name == "nt"
            results.append(
                {
                    "key_file": f.name,
                    "permissions": mode,
                    "secure": secure,
                }
            )
    return results


@server.tool("vault_status")
def vault_status(_args: Dict[str, Any]) -> Dict[str, Any]:
    items = _load_vault()
    ssh_keys = _audit_ssh_keys()
    return {
        "cipher": "PBKDF2-HMAC-SHA256 (100k iter) + Authenticated Stream",
        "secrets_count": len(items),
        "ssh_keys_audited": len(ssh_keys),
        "ssh_keys": ssh_keys,
        "vault_locked": False,
    }


@server.tool("store_secret")
def store_secret(args: Dict[str, Any]) -> Dict[str, Any]:
    label = str(args.get("label", "")).strip()
    category = str(args.get("category") or "password").strip().lower()
    secret_val = str(args.get("secret_value", ""))
    if not label or not secret_val:
        raise ConnectorError("Both 'label' and 'secret_value' are required.", code=-32602)
    if category not in {"password", "api_token", "ssh_key", "note"}:
        category = "password"

    items = [i for i in _load_vault() if i.get("label") != label]
    items.insert(
        0,
        {
            "label": label,
            "category": category,
            "ciphertext": _encrypt(secret_val),
            "updated_at": int(time.time()),
        },
    )
    _save_vault(items)
    return {
        "stored": True,
        "label": label,
        "category": category,
        "secrets_count": len(items),
    }


@server.tool("list_secrets")
def list_secrets(args: Dict[str, Any]) -> Dict[str, Any]:
    reveal = str(args.get("reveal_label") or "").strip()
    items = _load_vault()
    out: List[Dict[str, Any]] = []
    for item in items:
        lbl = str(item.get("label", ""))
        ct = str(item.get("ciphertext", ""))
        val_display = "••••••••••••••••"
        if reveal and (reveal == "*" or reveal.lower() == lbl.lower()):
            try:
                val_display = _decrypt(ct)
            except Exception:
                val_display = "[ERROR DE DESCIFRADO]"
        out.append(
            {
                "label": lbl,
                "category": item.get("category", "password"),
                "value": val_display,
                "updated_at": item.get("updated_at", 0),
            }
        )
    return {
        "count": len(out),
        "secrets": out,
    }


@server.tool("generate_entropy_key")
def generate_entropy_key(args: Dict[str, Any]) -> Dict[str, Any]:
    length = max(8, min(int(args.get("length") or 28), 128))
    include_symbols = bool(args.get("include_symbols", True))
    alphabet = string.ascii_letters + string.digits
    if include_symbols:
        alphabet += "!@#$%^&*()-_=+[]{}?"
    generated = "".join(secrets.choice(alphabet) for _ in range(length))
    entropy_bits = round(length * (6.1 if include_symbols else 5.95), 1)
    return {
        "generated_key": generated,
        "length": length,
        "entropy_bits": entropy_bits,
        "strength": "MILITARY_GRADE" if entropy_bits >= 128 else "STRONG",
    }


if __name__ == "__main__":
    server.run_stdio()

