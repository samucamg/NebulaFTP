"""Worker único: envia versões em staging ao canal, apaga mensagens velhas e roda a limpeza."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from ..blobs import Blobs
from ..store import Part, Store

log = logging.getLogger("nebula.worker")


class UploadWorker:
    def __init__(self, store: Store, blobs: Blobs, tg, wakeup: asyncio.Event, chunk_size: int,
                 max_cache_age: float = 3600, max_staging_age: float = 3600, gc_interval: float = 600):
        self.store = store
        self.blobs = blobs
        self.tg = tg
        self.wakeup = wakeup
        self.chunk_size = chunk_size
        self.max_cache_age = max_cache_age
        self.max_staging_age = max_staging_age
        self.gc_interval = gc_interval
        self._last_gc = time.time()
        self._stop = False

    def stop(self) -> None:
        self._stop = True
        self.wakeup.set()

    async def run(self) -> None:
        log.info("Worker de envio iniciado (%s pendentes)", await self.store.pending_count())
        while not self._stop:
            self.wakeup.clear()
            try:
                did = await self.step()
            except Exception:
                log.exception("erro no worker")
                did = False
            if not did:
                try:
                    await asyncio.wait_for(self.wakeup.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass

    async def step(self) -> bool:
        """Uma unidade de trabalho. Devolve True se fez algo."""
        trash = await self.store.trash_batch()
        if trash:
            try:
                await self.tg.delete(trash)
                await self.store.trash_done(trash)
            except Exception as e:
                log.warning("falha ao apagar mensagens antigas: %s", e)
        v = await self.store.next_pending(time.time())
        if v:
            await self.upload_version(v)
        if time.time() - self._last_gc > self.gc_interval:
            self._last_gc = time.time()
            n = await self.blobs.gc(self.max_cache_age, self.max_staging_age)
            if n:
                log.info("limpeza: %s arquivos locais removidos", n)
        return bool(v)

    async def upload_version(self, v) -> None:
        path = Path(v.staging_path)
        sent: list[Part] = []
        try:
            if not await self.store.get_version(v.id):
                raise _Superseded()
            if not path.exists():
                raise FileNotFoundError(f"staging ausente: {path}")
            real = path.stat().st_size
            if real != v.size:
                raise IOError(f"staging com {real} bytes, esperado {v.size}")
            self.blobs.lease(path)
            try:
                count = max(1, -(-v.size // self.chunk_size))
                for idx in range(count):
                    if not await self.store.get_version(v.id):
                        raise _Superseded()
                    name = v.name if count == 1 else f"{v.name}.part{idx + 1:03d}"
                    if count == 1:
                        s = await self.tg.upload(path, name)
                    else:
                        chunk = await asyncio.to_thread(self._cut, path, idx)
                        try:
                            s = await self.tg.upload(chunk, name)
                        finally:
                            self.blobs.remove_file(chunk)
                    sent.append(Part(idx, s.msg_id, s.file_id, s.size))
                    log.info("enviado %s parte %s/%s (%s bytes)", v.name, idx + 1, count, s.size)
            finally:
                self.blobs.release(path)
            if sum(p.size for p in sent) != v.size:
                raise IOError("soma das partes diferente do tamanho do arquivo")
            if await self.store.finish_upload(v.id, sent):
                self.blobs.remove_file(path)
            else:
                raise _Superseded()
        except _Superseded:
            if sent:
                await self.store.add_trash([p.msg_id for p in sent])
            log.info("versão %s substituída durante o envio; descartada", v.id)
        except Exception as e:
            if sent:
                await self.store.add_trash([p.msg_id for p in sent])
            delay = min(600, 5 * 2 ** min(v.attempts, 7))
            log.warning("envio de %s falhou (%s); nova tentativa em %ss", v.name, e, delay)
            await self.store.fail_upload(v.id, str(e), delay)

    def _cut(self, path: Path, idx: int) -> Path:
        out = self.blobs.staging_dir / f"{path.stem}.p{idx}.chunk"
        with open(path, "rb") as src, open(out, "wb") as dst:
            src.seek(idx * self.chunk_size)
            left = self.chunk_size
            while left > 0:
                b = src.read(min(left, 4 * 1024 * 1024))
                if not b:
                    break
                dst.write(b)
                left -= len(b)
        return out


class _Superseded(Exception):
    pass
