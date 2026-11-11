"""Configuração lida do .env (um bot, um canal, SQLite)."""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


@dataclass
class Settings:
    api_id: int = 0
    api_hash: str = ""
    bot_token: str = ""
    chat_id: int = 0
    db_file: Path = Path("nebula.db")
    data_dir: Path = Path("data")
    host: str = "0.0.0.0"
    sftp_port: int = 2222
    web_port: int = 8082
    admin_user: str = "admin"
    admin_password: str = ""
    chunk_size: int = 100 * 1024 * 1024
    max_staging_age: int = 3600
    cache_max_age: int = 3600
    log_level: str = "INFO"
    host_key: Path = Path("sftp_host_key")
    extra: dict = field(default_factory=dict)

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "staging"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "Settings":
        try:
            from dotenv import load_dotenv

            if env_file:
                load_dotenv(env_file)
        except ImportError:  # pragma: no cover
            pass
        tokens = os.getenv("BOT_TOKENS", "") or os.getenv("BOT_TOKEN", "")
        token = tokens.split(",")[0].strip()
        return cls(
            api_id=_int("API_ID", 0),
            api_hash=os.getenv("API_HASH", "").strip(),
            bot_token=token,
            chat_id=_int("CHAT_ID", 0),
            db_file=Path(os.getenv("DB_FILE", "nebula.db")),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            host=os.getenv("HOST", "0.0.0.0"),
            sftp_port=_int("SFTP_PORT", 2222),
            web_port=_int("WEB_PORT", 8082),
            admin_user=os.getenv("WEB_ADMIN_USER", "admin").strip() or "admin",
            admin_password=os.getenv("WEB_ADMIN_PASSWORD", ""),
            chunk_size=_int("CHUNK_SIZE_MB", 100) * 1024 * 1024,
            max_staging_age=_int("MAX_STAGING_AGE", 3600),
            cache_max_age=_int("CACHE_MAX_AGE", 3600),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            host_key=Path(os.getenv("SFTP_HOST_KEY", "sftp_host_key")),
        )


class _Redact(logging.Filter):
    """Remove segredos conhecidos de qualquer linha de log."""

    def __init__(self, secrets: list[str]):
        super().__init__()
        self.secrets = [s for s in secrets if s and len(s) >= 6]

    def filter(self, record: logging.LogRecord) -> bool:
        if self.secrets:
            msg = record.getMessage()
            for s in self.secrets:
                msg = msg.replace(s, "***")
            record.msg, record.args = msg, ()
        return True


def setup_logging(settings: Settings, log_file: str | None = "nebula.log") -> None:
    """Log em UTF-8 no console e no arquivo (Windows usa cp1252 por padrão)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    red = _Redact([settings.bot_token, settings.api_hash, settings.admin_password])
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(red)
        root.addHandler(h)
    for noisy in ("pyrogram", "asyncssh", "aiohttp.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
