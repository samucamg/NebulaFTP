"""Telegram simulado para testes: guarda os documentos em memória."""
from __future__ import annotations

import asyncio
import itertools
from pathlib import Path

from .backend import Sent


class FakeTelegram:
    def __init__(self, fail_uploads: int = 0, delay: float = 0.0):
        self.docs: dict[int, bytes] = {}
        self.names: dict[int, str] = {}
        self.deleted: list[int] = []
        self.uploads = 0
        self.downloads = 0
        self.fail_uploads = fail_uploads
        self.delay = delay
        self._ids = itertools.count(1)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def upload(self, path: Path, name: str) -> Sent:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_uploads > 0:
            self.fail_uploads -= 1
            raise ConnectionError("falha simulada de envio")
        data = Path(path).read_bytes()
        if not data:
            raise ValueError("Telegram não aceita documento vazio")
        mid = next(self._ids)
        self.docs[mid] = data
        self.names[mid] = name
        self.uploads += 1
        return Sent(mid, f"file{mid}", len(data))

    async def download(self, msg_id: int, file_id: str, dest: Path) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if msg_id not in self.docs:
            raise FileNotFoundError(f"mensagem {msg_id} não existe")
        self.downloads += 1
        tmp = Path(str(dest) + ".dl")
        tmp.write_bytes(self.docs[msg_id])
        tmp.replace(dest)

    async def delete(self, msg_ids: list[int]) -> None:
        for m in msg_ids:
            self.docs.pop(m, None)
            self.deleted.append(m)
