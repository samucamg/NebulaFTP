"""Montagem do serviço: banco, VFS, worker, SFTP e web."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .blobs import Blobs
from .config import Settings
from .store import Store
from .telegram.worker import UploadWorker
from .vfs import NebulaVFS

log = logging.getLogger("nebula")


@dataclass
class Core:
    settings: Settings
    store: Store
    blobs: Blobs
    vfs: NebulaVFS
    worker: UploadWorker
    tg: object


async def build_core(settings: Settings, tg) -> Core:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.db_file)
    await store.open()
    blobs = Blobs(store, tg, settings.staging_dir, settings.cache_dir, settings.chunk_size)
    vfs = NebulaVFS(store, blobs, admin_login=settings.admin_user)
    await vfs.init()
    worker = UploadWorker(
        store, blobs, tg, vfs.wakeup, settings.chunk_size,
        max_cache_age=settings.cache_max_age, max_staging_age=settings.max_staging_age,
    )
    return Core(settings, store, blobs, vfs, worker, tg)
