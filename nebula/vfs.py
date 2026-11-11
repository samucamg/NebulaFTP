"""NebulaVFS: o núcleo único. SFTP e web só chamam este módulo.

Cada usuário comum vê a própria pasta /<login> como a sua raiz '/'. Só o admin vê a raiz real.
"""
from __future__ import annotations

import asyncio
import hashlib
import sqlite3
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import security
from .blobs import Blobs
from .security import PathError
from .store import Node, Store, Version

log = logging.getLogger("nebula.vfs")


# ---------------- erros ----------------
class FSError(Exception):
    pass


class NotFound(FSError):
    pass


class Exists(FSError):
    pass


class NotADir(FSError):
    pass


class IsADir(FSError):
    pass


class NotEmpty(FSError):
    pass


class Denied(FSError):
    pass


class Invalid(FSError):
    pass


@dataclass(frozen=True)
class Principal:
    login: str
    is_admin: bool = False


@dataclass
class Stat:
    name: str
    path: str  # caminho virtual do usuário
    is_dir: bool
    size: int
    mtime: float
    node_id: int
    synced: bool = True


def _sha256_file(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
            size += len(b)
    return size, h.hexdigest()


class NebulaVFS:
    def __init__(self, store: Store, blobs: Blobs, admin_login: str = "admin"):
        self.store = store
        self.blobs = blobs
        self.admin_login = admin_login
        self.wakeup = asyncio.Event()  # acorda o worker quando há versão nova
        self._fails: dict[str, tuple[int, float]] = {}  # login -> (falhas, bloqueado_até)

    async def init(self) -> None:
        if not await self.store.get_node("/"):
            async with self.store.tx() as db:
                await self.store.insert_node(db, "/", "", "", "dir")

    # ---------------- caminhos ----------------
    def home(self, p: Principal) -> str:
        return "/" if p.is_admin else "/" + p.login

    def real(self, p: Principal, vpath: str) -> str:
        try:
            v = security.normalize(vpath or "/")
        except PathError as e:
            raise Denied(str(e)) from e
        if p.is_admin:
            return v
        return "/" + p.login + ("" if v == "/" else v)

    def virtual(self, p: Principal, real: str) -> str:
        if p.is_admin:
            return real
        home = "/" + p.login
        if real == home:
            return "/"
        if not real.startswith(home + "/"):
            raise Denied("fora da pasta do usuário")
        return real[len(home):]

    def _stat(self, p: Principal, n: Node) -> Stat:
        return Stat(
            name=n.name or "/",
            path=self.virtual(p, n.path),
            is_dir=n.is_dir,
            size=0 if n.is_dir else n.size,
            mtime=n.mtime,
            node_id=n.id,
            synced=n.is_dir or n.state != "staging",
        )

    async def _node(self, real: str) -> Node:
        n = await self.store.get_node(real)
        if not n:
            raise NotFound(real)
        return n

    async def _parent_dir(self, real: str) -> tuple[str, str]:
        parent, name = security.split(real)
        if not security.valid_name(name):
            raise Invalid("nome inválido")
        pn = await self.store.get_node(parent)
        if not pn:
            raise NotFound(parent)
        if not pn.is_dir:
            raise NotADir(parent)
        return parent, name

    # ---------------- consultas ----------------
    async def stat(self, p: Principal, vpath: str) -> Stat:
        return self._stat(p, await self._node(self.real(p, vpath)))

    async def stat_by_id(self, p: Principal, node_id: int) -> Stat:
        path = await self.store.path_of(node_id)
        if not path:
            raise NotFound(str(node_id))
        n = await self._node(path)
        return self._stat(p, n)  # virtual() nega se for de outro usuário

    async def listdir(self, p: Principal, vpath: str) -> list[Stat]:
        n = await self._node(self.real(p, vpath))
        if not n.is_dir:
            raise NotADir(vpath)
        return [self._stat(p, c) for c in await self.store.list_children(n.path)]

    # ---------------- pastas ----------------
    async def mkdir(self, p: Principal, vpath: str, exist_ok: bool = False) -> Stat:
        real = self.real(p, vpath)
        existing = await self.store.get_node(real)
        if existing:
            if existing.is_dir and exist_ok:
                return self._stat(p, existing)
            raise Exists(vpath)
        parent, name = await self._parent_dir(real)
        try:
            async with self.store.tx() as db:
                await self._check_parent_tx(parent)
                await self.store.insert_node(db, real, parent, name, "dir")
        except sqlite3.IntegrityError:
            raise Exists(vpath)
        return await self.stat(p, vpath)

    async def _check_parent_tx(self, parent: str) -> None:
        kind = await self.store.kind_of(parent)
        if not kind:
            raise NotFound(parent)
        if kind != "dir":
            raise NotADir(parent)

    async def rmdir(self, p: Principal, vpath: str) -> None:
        real = self.real(p, vpath)
        if real == self.home(p) or real == "/":
            raise Denied("não é possível remover a raiz")
        n = await self._node(real)
        if not n.is_dir:
            raise NotADir(vpath)
        async with self.store.tx() as db:
            if await self.store.list_children(real):
                raise NotEmpty(vpath)
            await self.store.delete_nodes(db, [n.id])

    # ---------------- remoção ----------------
    async def remove(self, p: Principal, vpath: str) -> None:
        """Remove um arquivo (SFTP)."""
        real = self.real(p, vpath)
        n = await self._node(real)
        if n.is_dir:
            raise IsADir(vpath)
        await self._delete_real(real)

    async def delete(self, p: Principal, vpath: str) -> None:
        """Remove arquivo ou pasta com todo o conteúdo (web)."""
        real = self.real(p, vpath)
        if real == self.home(p) or real == "/":
            raise Denied("não é possível remover a raiz")
        await self._node(real)
        await self._delete_real(real)

    async def _delete_real(self, real: str) -> None:
        stale: list[Optional[str]] = []
        async with self.store.tx() as db:
            nodes = await self.store.subtree(db, real)
            for n in nodes:
                if n.version_id:
                    stale.append(await self.store.kill_version(db, n.version_id))
            await self.store.delete_nodes(db, [n.id for n in nodes])
        for s in stale:
            self.blobs.remove_file(s)
        self.wakeup.set()

    # ---------------- renomear ----------------
    async def rename(self, p: Principal, src: str, dst: str, overwrite: bool = False) -> None:
        rs, rd = self.real(p, src), self.real(p, dst)
        home = self.home(p)
        if rs in ("/", home) or rd in ("/", home):
            raise Denied("não é possível renomear a raiz")
        if rs == rd:
            return
        if rd.startswith(rs.rstrip("/") + "/"):
            raise Invalid("não é possível mover uma pasta para dentro dela mesma")
        await self._node(rs)
        dparent, _ = await self._parent_dir(rd)
        stale: Optional[str] = None
        async with self.store.tx() as db:
            ns = await self.store.get_node(rs)
            if not ns:
                raise NotFound(src)
            await self._check_parent_tx(dparent)
            nd = await self.store.get_node(rd)
            if nd:
                if not overwrite or nd.is_dir or ns.is_dir:
                    raise Exists(dst)
                if nd.version_id:
                    stale = await self.store.kill_version(db, nd.version_id)
                await self.store.delete_nodes(db, [nd.id])
            await self.store.move_subtree(db, rs, rd)
        self.blobs.remove_file(stale)
        self.wakeup.set()

    async def set_mtime(self, p: Principal, vpath: str, mtime: float) -> None:
        n = await self._node(self.real(p, vpath))
        async with self.store.tx() as db:
            await self.store.set_mtime(db, n.id, mtime)

    # ---------------- gravação ----------------
    async def open_write(
        self, p: Principal, vpath: str, *, truncate: bool = True, append: bool = False,
        create: bool = True, exclusive: bool = False,
    ) -> "WriteHandle":
        real = self.real(p, vpath)
        n = await self.store.get_node(real)
        if n and n.is_dir:
            raise IsADir(vpath)
        if n and exclusive:
            raise Exists(vpath)
        if not n:
            if not create:
                raise NotFound(vpath)
            parent, name = await self._parent_dir(real)
            # cria já o arquivo vazio: open+close sem write precisa existir (RaiDrive/Explorer)
            try:
                async with self.store.tx() as db:
                    await self._check_parent_tx(parent)
                    vid = await self.store.add_version(db, 0, hashlib.sha256(b"").hexdigest(), "synced", None, name)
                    await self.store.insert_node(db, real, parent, name, "file", vid)
            except sqlite3.IntegrityError:
                if exclusive:
                    raise Exists(vpath)
            n = await self._node(real)
            truncate = True
        return WriteHandle(self, n, truncate=truncate, append=append)

    async def _commit(self, node: Node, staging: Path) -> None:
        size, digest = await asyncio.to_thread(_sha256_file, staging)
        name = node.name
        stale: Optional[str] = None
        async with self.store.tx() as db:
            current = await self.store.version_of(node.id)
            if not current:
                raise NotFound(node.path)  # apagado enquanto era gravado
            if size == 0:
                vid = await self.store.add_version(db, 0, digest, "synced", None, name)
            else:
                vid = await self.store.add_version(db, size, digest, "staging", str(staging), name)
            if current[0]:
                stale = await self.store.kill_version(db, current[0])
            await self.store.set_node_version(db, node.id, vid)
        if size == 0:
            self.blobs.remove_file(staging)
        self.blobs.remove_file(stale)
        self.wakeup.set()

    # ---------------- leitura ----------------
    async def open_read(self, p: Principal, vpath: str) -> "ReadHandle":
        n = await self._node(self.real(p, vpath))
        if n.is_dir:
            raise IsADir(vpath)
        return await ReadHandle.open(self, n)

    async def open_read_id(self, p: Principal, node_id: int) -> "ReadHandle":
        st = await self.stat_by_id(p, node_id)
        return await self.open_read(p, st.path)

    async def materialize_to(self, node: Node, dest: Path) -> None:
        """Copia o conteúdo atual do arquivo para dest (usado em append/escrita parcial)."""
        rh = await ReadHandle.open(self, node)
        try:
            with open(dest, "wb") as out:
                off = 0
                while True:
                    b = await rh.read(off, 4 * 1024 * 1024)
                    if not b:
                        break
                    out.write(b)
                    off += len(b)
        finally:
            await rh.close()

    # ---------------- usuários ----------------
    async def add_user(self, login: str, password: str, is_admin: bool = False) -> None:
        if not security.valid_login(login):
            raise Invalid("login deve ter 3 a 32 letras, números, _ ou -")
        if not password:
            raise Invalid("senha obrigatória")
        if await self.store.get_user(login):
            raise Exists(login)
        home = "/" + login
        try:
            async with self.store.tx() as db:
                await self.store.add_user(db, login, security.hash_password(password), is_admin)
                if not await self.store.kind_of(home):
                    await self.store.insert_node(db, home, "/", login, "dir")
        except sqlite3.IntegrityError:
            raise Exists(login)

    async def update_user(self, login: str, password: str | None = None, is_admin: bool | None = None) -> None:
        if not await self.store.get_user(login):
            raise NotFound(login)
        async with self.store.tx() as db:
            await self.store.update_user(
                db, login, security.hash_password(password) if password else None, is_admin
            )

    async def delete_user(self, login: str, delete_files: bool = False) -> None:
        if login == self.admin_login:
            raise Denied("o admin principal não pode ser removido")
        if not await self.store.get_user(login):
            raise NotFound(login)
        async with self.store.tx() as db:
            await self.store.delete_user(db, login)
        home = "/" + login
        if await self.store.get_node(home):
            if delete_files:
                await self._delete_real(home)
            else:
                # guarda os arquivos fora do alcance de um futuro usuário com o mesmo login
                kept = f"{home}.removido-{int(time.time())}"
                async with self.store.tx() as db:
                    await self.store.move_subtree(db, home, kept)

    async def authenticate(self, login: str, password: str, ip: str = "") -> Optional[Principal]:
        """Confere a senha. Depois de 5 erros seguidos do mesmo IP, esse login fica bloqueado
        por 60 s só para aquele IP (o usuário legítimo em outro IP continua entrando)."""
        key = f"{(login or '').lower()}|{ip}"
        now = time.time()
        if len(self._fails) > 10000:  # não deixa o dicionário crescer sem limite
            self._fails = {k: v for k, v in self._fails.items() if v[1] > now}
        fails, until = self._fails.get(key, (0, 0.0))
        if until > time.time():
            await asyncio.sleep(1)
            return None
        p = await self._check_password(login, password)
        if p:
            self._fails.pop(key, None)
        else:
            fails += 1
            self._fails[key] = (0, time.time() + 60) if fails >= 5 else (fails, 0.0)
            await asyncio.sleep(0.5)
        return p

    async def _check_password(self, login: str, password: str) -> Optional[Principal]:
        u = await self.store.get_user(login or "")
        if not u:
            security.verify_password(password or "", "scrypt$00$00")  # tempo parecido
            return None
        if not security.verify_password(password or "", u.password_hash):
            return None
        return Principal(u.login, u.is_admin)

    async def ensure_admin(self, login: str, password: str) -> None:
        """Cria o admin na primeira execução. Sem senha configurada, não cria."""
        u = await self.store.get_user(login)
        if u:
            if not u.is_admin:
                await self.update_user(login, is_admin=True)
            return
        if not password:
            raise Invalid("defina WEB_ADMIN_PASSWORD no .env para criar o admin")
        await self.add_user(login, password, is_admin=True)


class WriteHandle:
    """Arquivo aberto para escrita. O conteúdo vai para o staging e vira versão nova no close."""

    def __init__(self, vfs: NebulaVFS, node: Node, truncate: bool, append: bool):
        self.vfs = vfs
        self.node = node
        self.truncate = truncate
        self.append = append
        self.staging = vfs.blobs.new_staging()
        self._f = None
        self._dirty = truncate and node.size > 0  # truncar arquivo com conteúdo já muda o arquivo
        self._closed = False
        self._lock = asyncio.Lock()
        vfs.blobs.lease(self.staging)

    async def _ensure_open(self) -> None:
        if self._f is not None:
            return
        if not self.truncate and self.node.size > 0:
            await self.vfs.materialize_to(self.node, self.staging)
            self._f = open(self.staging, "r+b")
        else:
            self._f = open(self.staging, "w+b")

    async def write(self, data: bytes, offset: Optional[int] = None) -> int:
        async with self._lock:
            return await self._write(data, offset)

    async def _write(self, data: bytes, offset: Optional[int]) -> int:
        await self._ensure_open()
        if self.append or offset is None:
            self._f.seek(0, os.SEEK_END)
        else:
            self._f.seek(offset)
        self._f.write(data)
        self._dirty = True
        return len(data)

    async def read(self, offset: int, size: int) -> bytes:
        """Lê o conteúdo como está nesta escrita (arquivo aberto em leitura e escrita)."""
        async with self._lock:
            await self._ensure_open()
            self._f.seek(offset)
            return self._f.read(size)

    async def truncate_to(self, size: int) -> None:
        async with self._lock:
            await self._ensure_open()
            self._f.truncate(size)
            self._dirty = True

    def size(self) -> int:
        if self._f is None:
            return 0 if self.truncate else self.node.size
        pos = self._f.tell()
        self._f.seek(0, os.SEEK_END)
        end = self._f.tell()
        self._f.seek(pos)
        return end

    async def close(self) -> None:
        async with self._lock:
            await self._close()

    async def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._dirty:
                await self._ensure_open()
                self._f.close()
                self._f = None
                try:
                    await self.vfs._commit(self.node, self.staging)
                except BaseException:
                    self.vfs.blobs.remove_file(self.staging)
                    raise
            else:
                if self._f:
                    self._f.close()
                self.vfs.blobs.remove_file(self.staging)
        finally:
            self.vfs.blobs.release(self.staging)

    async def abort(self) -> None:
        self._closed = True
        if self._f:
            self._f.close()
        self.vfs.blobs.release(self.staging)
        self.vfs.blobs.remove_file(self.staging)


class ReadHandle:
    """Leitura por offset. Usa o staging local se existir; senão baixa só as partes necessárias."""

    def __init__(self, vfs: NebulaVFS, version: Version, local: Optional[Path], parts):
        self.vfs = vfs
        self.version = version
        self.size = version.size
        self.local = local
        self.parts = parts
        self._starts = []
        acc = 0
        for prt in parts:
            self._starts.append(acc)
            acc += prt.size
        self._cur_idx: Optional[int] = None
        self._cur_f = None
        self._cur_path: Optional[Path] = None
        self._local_f = None
        self._prefetch: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @classmethod
    async def open(cls, vfs: NebulaVFS, node: Node) -> "ReadHandle":
        for _ in range(3):
            v = await vfs.store.get_version(node.version_id) if node.version_id else None
            if v is None:
                raise NotFound(node.path)
            if v.size == 0:
                return cls(vfs, v, None, [])
            if v.staging_path:
                path = Path(v.staging_path)
                try:
                    h = cls(vfs, v, path, [])
                    h._local_f = open(path, "rb")
                    vfs.blobs.lease(path)
                    return h
                except FileNotFoundError:
                    node = await vfs._node(node.path)  # o worker acabou de enviar; tenta pelas partes
                    continue
            parts = await vfs.store.get_parts(v.id)
            if not parts:
                raise NotFound(node.path)
            return cls(vfs, v, None, parts)
        raise NotFound(node.path)

    def _part_for(self, offset: int) -> int:
        lo, hi = 0, len(self._starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    async def _switch(self, idx: int) -> None:
        if self._cur_idx == idx:
            return
        self._drop_current()
        path = await self.vfs.blobs.ensure_part(self.version.id, self.parts[idx])
        f = open(path, "rb")
        self.vfs.blobs.lease(path)
        self._cur_path = path
        self._cur_f = f
        self._cur_idx = idx
        if idx + 1 < len(self.parts) and (self._prefetch is None or self._prefetch.done()):
            nxt = self.parts[idx + 1]
            self._prefetch = asyncio.create_task(self._safe_prefetch(nxt))

    async def _safe_prefetch(self, part) -> None:
        try:
            await self.vfs.blobs.ensure_part(self.version.id, part)
        except Exception as e:  # a leitura de verdade tenta de novo
            log.debug("pré-busca falhou: %s", e)

    def _drop_current(self) -> None:
        if self._cur_f:
            self._cur_f.close()
            self.vfs.blobs.release(self._cur_path)
        self._cur_f = self._cur_path = self._cur_idx = None

    async def read(self, offset: int, size: int) -> bytes:
        async with self._lock:
            return await self._read(offset, size)

    async def _read(self, offset: int, size: int) -> bytes:
        if offset >= self.size or size <= 0:
            return b""
        size = min(size, self.size - offset)
        if self._local_f:
            self._local_f.seek(offset)
            return self._local_f.read(size)
        out = bytearray()
        while size > 0:
            idx = self._part_for(offset)
            await self._switch(idx)
            rel = offset - self._starts[idx]
            self._cur_f.seek(rel)
            chunk = self._cur_f.read(min(size, self.parts[idx].size - rel))
            if not chunk:
                raise IOError("parte truncada no cache")
            out += chunk
            offset += len(chunk)
            size -= len(chunk)
        return bytes(out)

    async def close(self) -> None:
        async with self._lock:
            self._drop_current()
            if self._local_f:
                self._local_f.close()
                self.vfs.blobs.release(self.local)
                self._local_f = None
