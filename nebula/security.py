"""Senhas, logins e caminhos virtuais."""
from __future__ import annotations

import hashlib
import hmac
import posixpath
import re
import secrets
import unicodedata

LOGIN_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


class PathError(ValueError):
    """Caminho inválido ou fora da raiz virtual."""


def valid_login(login: str) -> bool:
    return bool(login) and bool(LOGIN_RE.match(login))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, dk_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), **_SCRYPT)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def valid_name(name: str) -> bool:
    return bool(name) and name not in (".", "..") and "/" not in name and "\\" not in name and "\x00" not in name


def normalize(path: str) -> str:
    """Normaliza um caminho virtual absoluto. '..' na raiz fica na raiz (nunca sai dela).

    Barras invertidas são tratadas como separadores (clientes Windows)."""
    if path is None:
        raise PathError("caminho vazio")
    if "\x00" in path:
        raise PathError("caractere nulo")
    path = unicodedata.normalize("NFC", path.replace("\\", "/"))
    parts: list[str] = []
    for comp in path.split("/"):
        if comp in ("", "."):
            continue
        if comp == "..":
            if parts:  # ".." na raiz continua na raiz (POSIX); nunca sai dela
                parts.pop()
            continue
        parts.append(comp)
    return "/" + "/".join(parts)


def join(base: str, name: str) -> str:
    return normalize(posixpath.join(base, name))


def split(path: str) -> tuple[str, str]:
    path = normalize(path)
    if path == "/":
        return "/", ""
    parent, name = posixpath.split(path)
    return parent or "/", name
