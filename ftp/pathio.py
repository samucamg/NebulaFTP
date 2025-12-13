from asyncio import CancelledError, get_event_loop, gather, sleep as asleep, Lock
from collections import namedtuple
from functools import wraps
from io import BytesIO
from os import environ
from pathlib import PurePosixPath
from sys import exc_info
from time import time
from uuid import uuid4
import os
import aiofiles
import logging
import unicodedata
import re

from .errors import PathIOError
from .tg import File
from .common import UPLOAD_QUEUE

logger = logging.getLogger("NebulaFTP")

__all__ = ("AbstractPathIO", "PathIONursery", "MongoDBPathIO")

CACHE_DIR = "staging"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def universal_exception(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        try:
            return await coro(*args, **kwargs)
        except (CancelledError, NotImplementedError, StopAsyncIteration):
            raise
        except Exception as exc:
            raise PathIOError(reason=exc_info()) from exc
    return wrapper

class PathIONursery:
    def __init__(self, factory):
        self.factory = factory
        self.state = None

    def __call__(self, *args, **kwargs):
        instance = self.factory(*args, state=self.state, **kwargs)
        if self.state is None:
            self.state = instance.state
        return instance

class AbstractPathIO:
    def __init__(self, connection=None):
        self.connection = connection

class Node:
    def __init__(self, type, name, ctime=None, mtime=None, size=0, parent="/", parts=None, local_path=None, **k):
        if parts is None: parts = []
        self.type = type
        self.name = name
        self.ctime = ctime or int(time())
        self.mtime = mtime or int(time())
        self.size = size
        self.parent = parent
        self.path = str(PurePosixPath(parent) / name)
        self.parts = parts
        self.local_path = local_path

class MongoDBMemoryIO:
    def __init__(self, node, mode, tg, db):
        self._node = node; self._mode = mode; self._tg = tg; self._db = db
        self.offset = 0
        self.safe_name = f"{uuid4().hex}_{node.name}"
        self.local_path = os.path.join(CACHE_DIR, self.safe_name)

    async def __aenter__(self): return self
    async def __aexit__(self, *args, **kwargs): pass
    async def seek(self, offset=0): self.offset = offset

    async def write_stream(self, stream):
        try:
            async with aiofiles.open(self.local_path, "wb") as f:
                if self.offset > 0: await f.seek(self.offset)
                async for data in stream.iter_by_block(1024*1024):
                    await f.write(data)
                await f.flush()
        except Exception as e:
            logger.error(f"❌ [WRITE] Erro disco: {e}"); raise

        final_size = os.path.getsize(self.local_path)
        parent = self._node.parent
        name = self._node.name
        cache_key = f"{parent}::{name}"
        now = int(time())

        doc_cache = {
            "type": "file", "name": name, "parent": parent, "size": final_size,
            "status": "staging", "local_path": self.local_path,
            "mtime": now, "ctime": now, "parts": []
        }

        # Atualiza Cache (Prioridade para Rclone)
        async with MongoDBPathIO._cache_lock:
            MongoDBPathIO._memory_cache[cache_key] = doc_cache

        # Atualiza DB em background (best effort)
        try:
            await self._db.files.replace_one({"name": name, "parent": parent}, doc_cache, upsert=True)
        except: pass

        # 🛑 GARANTIA: NUNCA enfileira .partial aqui
        if not name.endswith(".partial") and final_size > 0:
             await UPLOAD_QUEUE.put({
                "path": self.local_path, "filename": name, "parent": parent, "size": final_size
            })
             logger.info(f"📤 [WRITE] Upload direto enfileirado: {name}")
        elif name.endswith(".partial"):
             # Apenas log para debug, mas não enfileira
             logger.debug(f"⏳ [WRITE] Aguardando rename para: {name}")

    async def iter_by_block(self, block_size):
        if self._node.local_path and os.path.exists(self._node.local_path):
            async with aiofiles.open(self._node.local_path, 'rb') as f:
                await f.seek(self.offset)
                while True:
                    chunk = await f.read(block_size)
                    if not chunk: break
                    yield chunk
            return

        parts = self._node.parts
        if not parts: return
        parts.sort(key=lambda x: x["part_id"])
        current_file_pos = 0; start_read_at = self.offset

        for part in parts:
            part_size = part.get("file_size", 2 * 1024 * 1024 * 1024)
            part_end = current_file_pos + part_size
            if part_end <= start_read_at: current_file_pos += part_size; continue
            local_offset = max(0, start_read_at - current_file_pos)
            file = File(part["tg_file"], self._tg)
            async for chunk in file.stream(offset=local_offset): yield chunk
            current_file_pos += part_size; start_read_at = current_file_pos

class MongoDBPathIO(AbstractPathIO):
    db = None; tg = None
    _memory_cache = {}
    _cache_lock = Lock()
    Stats = namedtuple("Stats", ("st_size", "st_ctime", "st_mtime", "st_nlink", "st_mode"))

    def __init__(self, *args, state=None, cwd=None, **kwargs):
        super().__init__(*args, **kwargs); self.cwd = PurePosixPath("/")

    @property
    def state(self): return []

    def _absolute(self, path):
        if not path.is_absolute(): path = self.cwd / path
        return path

    def _sanitize(self, text):
        if not text: return ""
        return unicodedata.normalize('NFC', str(text))

    def _split_path(self, path_obj):
        p_str = self._sanitize(path_obj.as_posix())
        if not p_str.startswith("/"): p_str = "/" + p_str
        if p_str != "/" and p_str.endswith("/"): p_str = p_str[:-1]
        return os.path.dirname(p_str), os.path.basename(p_str)

    async def get_node(self, path):
        if str(path) in ("/", "."): return Node("dir", "", 0, 0, size=0, parent="/")
        parent, name = self._split_path(path)
        cache_key = f"{parent}::{name}"

        async with self._cache_lock:
            if cache_key in self._memory_cache:
                return Node(**self._memory_cache[cache_key])

        node = await self.db.files.find_one({"name": name, "parent": parent})
        if node:
            async with self._cache_lock: self._memory_cache[cache_key] = node
            return Node(**node)
            
        # Fallback
        if parent.startswith("/") and parent != "/":
            alt = parent[1:]
            node = await self.db.files.find_one({"name": name, "parent": alt})
            if node:
                async with self._cache_lock: self._memory_cache[cache_key] = node
                return Node(**node)
        return None

    @universal_exception
    async def exists(self, path): return (await self.get_node(self._absolute(path))) is not None

    @universal_exception
    async def is_dir(self, path):
        node = await self.get_node(self._absolute(path))
        return not (node is None or node.type != "dir")

    @universal_exception
    async def is_file(self, path):
        node = await self.get_node(self._absolute(path))
        return not (node is None or node.type != "file")

    @universal_exception
    async def mkdir(self, path, *, exist_ok=False):
        path = self._absolute(path)
        if await self.get_node(path):
            if not exist_ok: raise FileExistsError
        else:
            parent, name = self._split_path(path)
            doc = {"type": "dir", "ctime": int(time()), "mtime": int(time()), "name": name, "parent": parent, "size": 0}
            try:
                await self.db.files.insert_one(doc)
                async with self._cache_lock: self._memory_cache[f"{parent}::{name}"] = doc
            except: 
                if not exist_ok: raise FileExistsError

    @universal_exception
    async def rmdir(self, path):
        path = self._absolute(path)
        parent, name = self._split_path(path)
        key = f"{parent}::{name}"
        async with self._cache_lock: self._memory_cache.pop(key, None)
        await self.db.files.delete_one({"name": name, "parent": parent})
        full = f"{parent}/{name}" if parent != "/" else f"/{name}"
        await self.db.files.delete_many({"parent": {"$regex": f"^{full}"}})

    @universal_exception
    async def unlink(self, path):
        path = self._absolute(path)
        node = await self.get_node(path)
        if node:
            async with self._cache_lock: self._memory_cache.pop(f"{node.parent}::{node.name}", None)
            raw = await self.db.files.find_one({"name": node.name, "parent": node.parent})
            if raw and "local_path" in raw and os.path.exists(raw["local_path"]):
                try: os.remove(raw["local_path"])
                except: pass
            await self.db.files.delete_one({"name": node.name, "parent": node.parent})

    def list(self, path):
        path = self._absolute(path)
        search = path.as_posix()
        if not search.startswith("/"): search = "/" + search
        if search != "/" and search.endswith("/"): search = search[:-1]

        class Lister:
            iter = None
            def __aiter__(self): return self
            @universal_exception
            async def __anext__(cls):
                if cls.iter is None:
                    cls.iter = self.db.files.find({"parent": search, "name": {"$not": {"$regex": r"\.partial$"}}})
                try:
                    doc = await cls.iter.__anext__()
                    return path / doc["name"]
                except StopAsyncIteration: raise
        return Lister()

    @universal_exception
    async def stat(self, path):
        node = await self.get_node(self._absolute(path))
        if node is None: raise FileNotFoundError
        mode = (0x8000 | 0o666) if node.type == "file" else (0x4000 | 0o777)
        return MongoDBPathIO.Stats(node.size, node.ctime, node.mtime, 1, mode)

    @universal_exception
    async def open(self, path, mode="rb", *args, **kwargs):
        path = self._absolute(path)
        parent, name = self._split_path(path)
        if mode == "wb":
            doc = {"type": "file", "ctime": int(time()), "mtime": int(time()), "name": name, "parent": parent, "size": 0, "parts": []}
            async with self._cache_lock: self._memory_cache[f"{parent}::{name}"] = doc
            await self.db.files.replace_one({"name": name, "parent": parent}, doc, upsert=True)
        
        node = await self.get_node(path)
        if not node and mode == "rb": raise FileNotFoundError
        return MongoDBMemoryIO(node, mode, self.tg, self.db)

    @universal_exception
    async def rename(self, source, destination):
        source = self._absolute(source); destination = self._absolute(destination)
        # logger.info(f"🔄 [RENAME] {source} → {destination}")

        src_p, src_n = self._split_path(source)
        dst_p, dst_n = self._split_path(destination)
        
        # 1. BUSCA ORIGEM NO CACHE PRIMEIRO
        old_key = f"{src_p}::{src_n}"
        new_key = f"{dst_p}::{dst_n}"
        src_doc = None

        async with self._cache_lock:
            src_doc = self._memory_cache.get(old_key)
        
        if not src_doc:
            src_doc = await self.db.files.find_one({"name": src_n, "parent": src_p})
        
        if not src_doc:
            logger.warning(f"⚠️ [RENAME] Origem não encontrada: {source}")
            return 

        # 2. Atualiza Cache Atomicamente
        async with self._cache_lock:
            self._memory_cache.pop(old_key, None)
            
            src_doc["name"] = dst_n
            src_doc["parent"] = dst_p
            src_doc["mtime"] = int(time())
            
            self._memory_cache[new_key] = src_doc

        # 3. Atualiza DB
        await self.db.files.update_one(
            {"_id": src_doc["_id"]}, 
            {"$set": {"name": dst_n, "parent": dst_p, "mtime": int(time())}}
        )

        # 4. Dispara Upload (Partial -> Final)
        if src_n.endswith(".partial") and not dst_n.endswith(".partial"):
            local_p = src_doc.get("local_path")
            
            if local_p and os.path.exists(local_p):
                await UPLOAD_QUEUE.put({
                    "path": local_p,
                    "filename": dst_n,
                    "parent": dst_p,
                    "size": src_doc.get("size", 0)
                })
                logger.info(f"📤 [RENAME] Enfileirado: {dst_n}")
            else:
                logger.warning(f"⚠️ [RENAME] Arquivo físico não encontrado: {dst_n}")
