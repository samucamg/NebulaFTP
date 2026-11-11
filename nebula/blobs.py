"""Staging e cache de partes. Dono único dos arquivos locais."""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path

from .store import Part, Store

log = logging.getLogger("nebula.blobs")


class Blobs:
    def __init__(self, store: Store, tg, staging_dir: Path, cache_dir: Path, chunk_size: int):
        self.store = store
        self.tg = tg
        self.staging_dir = Path(staging_dir)
        self.cache_dir = Path(cache_dir)
        self.chunk_size = chunk_size
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._leases: dict[str, int] = {}
        self._dl_sem = asyncio.Semaphore(2)  # um bot: poucos downloads ao mesmo tempo

    # ---------- staging ----------
    def new_staging(self) -> Path:
        return self.staging_dir / f"{uuid.uuid4().hex}.tmp"

    def remove_file(self, path: str | Path | None) -> None:
        if not path:
            return
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:  # Windows: arquivo aberto por um leitor; o GC tenta depois
            log.debug("não removido agora (%s): %s", path, e)

    # ---------- leases ----------
    def lease(self, path: Path) -> None:
        k = str(path)
        self._leases[k] = self._leases.get(k, 0) + 1

    def release(self, path: Path) -> None:
        k = str(path)
        n = self._leases.get(k, 0) - 1
        if n <= 0:
            self._leases.pop(k, None)
        else:
            self._leases[k] = n

    def in_use(self, path: str | Path) -> bool:
        return str(path) in self._leases

    # ---------- cache de partes ----------
    def part_path(self, vid: int, idx: int) -> Path:
        return self.cache_dir / f"v{vid}_p{idx}.bin"

    async def ensure_part(self, vid: int, part: Part) -> Path:
        """Baixa a parte para o cache (uma vez só por chave) e devolve o caminho."""
        dest = self.part_path(vid, part.idx)
        key = str(dest)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if dest.exists() and dest.stat().st_size == part.size:
                try:
                    os.utime(dest, None)
                except OSError:
                    pass
                return dest
            async with self._dl_sem:
                tmp = Path(key + ".part")
                await self.tg.download(part.msg_id, part.file_id, tmp)
                if tmp.stat().st_size != part.size:
                    self.remove_file(tmp)
                    raise IOError(f"parte {part.idx} da versão {vid} com tamanho errado")
                os.replace(tmp, dest)
            return dest

    async def gc(self, max_cache_age: float, max_staging_age: float) -> int:
        """Apaga cache antigo e staging órfão que ninguém está usando."""
        removed = 0
        now = time.time()
        for f in self.cache_dir.iterdir():
            try:
                age = now - f.stat().st_mtime
                if f.name.endswith((".part", ".dl")) and age < max(max_cache_age, 3600):
                    continue  # download em andamento
                if self.in_use(f) or age <= max_cache_age:
                    continue
                f.unlink()
                removed += 1
            except OSError:
                pass
        referenced = await self.store.staging_paths()
        for f in self.staging_dir.iterdir():
            if str(f) in referenced or self.in_use(f):
                continue
            try:
                if now - f.stat().st_mtime > max_staging_age:
                    f.unlink()
                    removed += 1
            except OSError:
                pass
        return removed
