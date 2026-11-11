"""Interface do armazenamento no Telegram e implementação com pyrofork (um bot, um canal)."""
from __future__ import annotations

import asyncio
import email.utils
import logging
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

log = logging.getLogger("nebula.telegram")


@dataclass
class Sent:
    msg_id: int
    file_id: str
    size: int


class TelegramBackend(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def upload(self, path: Path, name: str) -> Sent: ...
    async def download(self, msg_id: int, file_id: str, dest: Path) -> None: ...
    async def delete(self, msg_ids: list[int]) -> None: ...


def clock_offset(url: str = "https://api.telegram.org") -> float | None:
    """Diferença em segundos entre o relógio local e o do servidor (cabeçalho Date)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            date = resp.headers.get("Date")
    except urllib.error.HTTPError as e:  # 4xx ainda traz Date
        date = e.headers.get("Date")
    except Exception:
        return None
    if not date:
        return None
    return email.utils.parsedate_to_datetime(date).timestamp() - time.time()


class PyroBackend:
    """Backend real com pyrofork. Trata FloodWait esperando o tempo pedido."""

    def __init__(self, api_id: int, api_hash: str, bot_token: str, chat_id: int, workdir: str = "."):
        from pyrogram import Client

        self.chat_id = chat_id
        self.client = Client(
            "nebula_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token, workdir=workdir, no_updates=True
        )

    async def start(self) -> None:
        await self.client.start()
        chat = await self.client.get_chat(self.chat_id)
        log.info("Canal conectado: %s", getattr(chat, "title", self.chat_id))

    async def stop(self) -> None:
        try:
            await self.client.stop()
        except Exception:
            pass

    async def _retry(self, fn, *args, **kw):
        from pyrogram.errors import FloodWait

        for attempt in range(8):
            try:
                return await fn(*args, **kw)
            except FloodWait as e:
                wait = int(getattr(e, "value", 30) or 30) + 1
                log.warning("FloodWait: aguardando %ss", wait)
                await asyncio.sleep(wait)
        raise RuntimeError("FloodWait persistente")

    async def upload(self, path: Path, name: str) -> Sent:
        msg = await self._retry(
            self.client.send_document, self.chat_id, str(path), file_name=name, force_document=True
        )
        doc = msg.document
        return Sent(msg.id, doc.file_id, doc.file_size)

    async def download(self, msg_id: int, file_id: str, dest: Path) -> None:
        tmp = dest.with_suffix(dest.suffix + ".dl")
        await self._retry(self.client.download_media, file_id, file_name=str(tmp))
        tmp.replace(dest)

    async def delete(self, msg_ids: list[int]) -> None:
        for i in range(0, len(msg_ids), 100):
            await self._retry(self.client.delete_messages, self.chat_id, msg_ids[i : i + 100])
