"""Único acesso ao banco SQLite (WAL). Nenhum outro módulo escreve SQL."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    parent TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('dir','file')),
    mtime REAL NOT NULL,
    version_id INTEGER
);
CREATE INDEX IF NOT EXISTS nodes_parent ON nodes(parent);
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY,
    size INTEGER NOT NULL,
    sha256 TEXT,
    state TEXT NOT NULL CHECK (state IN ('staging','synced','dead')),
    staging_path TEXT,
    name TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_try REAL NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS parts (
    version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    msg_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    size INTEGER NOT NULL,
    PRIMARY KEY (version_id, idx)
);
CREATE TABLE IF NOT EXISTS trash (
    msg_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    login TEXT NOT NULL,
    csrf TEXT NOT NULL,
    expires REAL NOT NULL
);
"""


@dataclass
class Node:
    id: int
    path: str
    parent: str
    name: str
    kind: str
    mtime: float
    version_id: Optional[int]
    size: int = 0
    state: Optional[str] = None

    @property
    def is_dir(self) -> bool:
        return self.kind == "dir"


@dataclass
class Version:
    id: int
    size: int
    sha256: Optional[str]
    state: str
    staging_path: Optional[str]
    name: str
    attempts: int = 0


@dataclass
class Part:
    idx: int
    msg_id: int
    file_id: str
    size: int


@dataclass
class User:
    id: int
    login: str
    password_hash: str
    is_admin: bool


_NODE_SQL = (
    "SELECT n.id,n.path,n.parent,n.name,n.kind,n.mtime,n.version_id,"
    "COALESCE(v.size,0),v.state FROM nodes n LEFT JOIN versions v ON v.id=n.version_id"
)


def _node(row) -> Node:
    return Node(*row[:7], size=row[7], state=row[8])


class Store:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        self.db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        self.db = await aiosqlite.connect(self.db_file)
        await self.db.execute("PRAGMA journal_mode=WAL")
        await self.db.execute("PRAGMA foreign_keys=ON")
        await self.db.execute("PRAGMA busy_timeout=5000")
        await self.db.executescript(SCHEMA)
        await self.db.commit()

    async def close(self) -> None:
        if self.db:
            await self.db.close()
            self.db = None

    @asynccontextmanager
    async def tx(self):
        """Transação exclusiva. Qualquer exceção desfaz tudo."""
        async with self._lock:
            await self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except BaseException:
                await self.db.rollback()
                raise
            else:
                await self.db.commit()

    async def _one(self, sql, args=()):
        async with self.db.execute(sql, args) as cur:
            return await cur.fetchone()

    async def _all(self, sql, args=()):
        async with self.db.execute(sql, args) as cur:
            return await cur.fetchall()

    # ---------------- usuários ----------------
    async def get_user(self, login: str) -> Optional[User]:
        r = await self._one("SELECT id,login,password_hash,is_admin FROM users WHERE login=?", (login,))
        return User(r[0], r[1], r[2], bool(r[3])) if r else None

    async def list_users(self) -> list[User]:
        rows = await self._all("SELECT id,login,password_hash,is_admin FROM users ORDER BY login")
        return [User(r[0], r[1], r[2], bool(r[3])) for r in rows]

    async def add_user(self, db, login: str, password_hash: str, is_admin: bool) -> None:
        await db.execute(
            "INSERT INTO users(login,password_hash,is_admin,created_at) VALUES(?,?,?,?)",
            (login, password_hash, int(is_admin), time.time()),
        )

    async def update_user(self, db, login: str, password_hash: str | None, is_admin: bool | None) -> None:
        if password_hash is not None:
            await db.execute("UPDATE users SET password_hash=? WHERE login=?", (password_hash, login))
        if is_admin is not None:
            await db.execute("UPDATE users SET is_admin=? WHERE login=?", (int(is_admin), login))

    async def delete_user(self, db, login: str) -> None:
        await db.execute("DELETE FROM users WHERE login=?", (login,))
        await db.execute("DELETE FROM sessions WHERE login=?", (login,))

    # ---------------- sessões web ----------------
    async def add_session(self, token: str, login: str, csrf: str, expires: float) -> None:
        async with self.tx() as db:
            await db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            await db.execute("INSERT INTO sessions VALUES(?,?,?,?)", (token, login, csrf, expires))

    async def get_session(self, token: str):
        r = await self._one("SELECT login,csrf,expires FROM sessions WHERE token=?", (token,))
        if not r or r[2] < time.time():
            return None
        return r[0], r[1]

    async def delete_session(self, token: str) -> None:
        async with self.tx() as db:
            await db.execute("DELETE FROM sessions WHERE token=?", (token,))

    # ---------------- nós ----------------
    async def get_node(self, path: str) -> Optional[Node]:
        r = await self._one(_NODE_SQL + " WHERE n.path=?", (path,))
        return _node(r) if r else None

    async def list_children(self, path: str) -> list[Node]:
        rows = await self._all(_NODE_SQL + " WHERE n.parent=? AND n.path<>'/' ORDER BY n.kind, n.name", (path,))
        return [_node(r) for r in rows]

    async def path_of(self, node_id: int) -> Optional[str]:
        r = await self._one("SELECT path FROM nodes WHERE id=?", (node_id,))
        return r[0] if r else None

    async def kind_of(self, path: str) -> Optional[str]:
        r = await self._one("SELECT kind FROM nodes WHERE path=?", (path,))
        return r[0] if r else None

    async def version_of(self, node_id: int):
        """Devolve (version_id,) do nó ou None se o nó não existe."""
        return await self._one("SELECT version_id FROM nodes WHERE id=?", (node_id,))

    async def subtree(self, db, path: str) -> list[Node]:
        prefix = path.rstrip("/") + "/"
        rows = await self._all(
            _NODE_SQL + " WHERE n.path=? OR substr(n.path,1,?)=?", (path, len(prefix), prefix)
        )
        return [_node(r) for r in rows]

    async def insert_node(self, db, path, parent, name, kind, version_id=None, mtime=None) -> int:
        cur = await db.execute(
            "INSERT INTO nodes(path,parent,name,kind,mtime,version_id) VALUES(?,?,?,?,?,?)",
            (path, parent, name, kind, mtime or time.time(), version_id),
        )
        return cur.lastrowid

    async def set_node_version(self, db, node_id: int, version_id: int, mtime: float | None = None) -> None:
        await db.execute(
            "UPDATE nodes SET version_id=?, mtime=? WHERE id=?", (version_id, mtime or time.time(), node_id)
        )

    async def set_mtime(self, db, node_id: int, mtime: float) -> None:
        await db.execute("UPDATE nodes SET mtime=? WHERE id=?", (mtime, node_id))

    async def delete_nodes(self, db, ids: list[int]) -> None:
        await db.executemany("DELETE FROM nodes WHERE id=?", [(i,) for i in ids])

    async def move_subtree(self, db, old: str, new: str) -> None:
        """Renomeia o nó e todos os descendentes na mesma transação."""
        prefix = old.rstrip("/") + "/"
        rows = await self._all(
            "SELECT id,path,parent FROM nodes WHERE path=? OR substr(path,1,?)=?", (old, len(prefix), prefix)
        )
        for nid, path, parent in rows:
            np = new + path[len(old):]
            npar = parent if path == old else new + parent[len(old):]
            if path == old:
                from .security import split

                npar, nname = split(new)
                await db.execute("UPDATE nodes SET path=?,parent=?,name=? WHERE id=?", (np, npar, nname, nid))
            else:
                await db.execute("UPDATE nodes SET path=?,parent=? WHERE id=?", (np, npar, nid))

    # ---------------- versões e partes ----------------
    async def add_version(self, db, size, sha256, state, staging_path, name) -> int:
        cur = await db.execute(
            "INSERT INTO versions(size,sha256,state,staging_path,name,created_at) VALUES(?,?,?,?,?,?)",
            (size, sha256, state, staging_path, name, time.time()),
        )
        return cur.lastrowid

    async def get_version(self, vid: int) -> Optional[Version]:
        r = await self._one(
            "SELECT id,size,sha256,state,staging_path,name,attempts FROM versions WHERE id=?", (vid,)
        )
        return Version(*r) if r else None

    async def get_parts(self, vid: int) -> list[Part]:
        rows = await self._all("SELECT idx,msg_id,file_id,size FROM parts WHERE version_id=? ORDER BY idx", (vid,))
        return [Part(*r) for r in rows]

    async def kill_version(self, db, vid: int) -> Optional[str]:
        """Marca a versão como morta, manda suas partes para o lixo e devolve o staging a apagar."""
        r = await self._one("SELECT staging_path FROM versions WHERE id=?", (vid,))
        if not r:
            return None
        await db.execute("INSERT OR IGNORE INTO trash(msg_id) SELECT msg_id FROM parts WHERE version_id=?", (vid,))
        await db.execute("DELETE FROM versions WHERE id=?", (vid,))
        return r[0]

    async def is_current(self, vid: int) -> bool:
        return bool(await self._one("SELECT 1 FROM nodes WHERE version_id=?", (vid,)))

    async def next_pending(self, now: float) -> Optional[Version]:
        r = await self._one(
            "SELECT id,size,sha256,state,staging_path,name,attempts FROM versions "
            "WHERE state='staging' AND size>0 AND next_try<=? ORDER BY next_try, id LIMIT 1",
            (now,),
        )
        return Version(*r) if r else None

    async def pending_count(self) -> int:
        r = await self._one("SELECT COUNT(*) FROM versions WHERE state='staging' AND size>0")
        return r[0]

    async def finish_upload(self, vid: int, parts: list[Part]) -> bool:
        """Grava as partes e marca a versão como sincronizada. Devolve False se a versão sumiu."""
        async with self.tx() as db:
            if not await self._one("SELECT 1 FROM versions WHERE id=?", (vid,)):
                return False
            await db.executemany(
                "INSERT INTO parts(version_id,idx,msg_id,file_id,size) VALUES(?,?,?,?,?)",
                [(vid, p.idx, p.msg_id, p.file_id, p.size) for p in parts],
            )
            await db.execute("UPDATE versions SET state='synced', staging_path=NULL WHERE id=?", (vid,))
            return True

    async def fail_upload(self, vid: int, error: str, retry_in: float) -> None:
        async with self.tx() as db:
            await db.execute(
                "UPDATE versions SET attempts=attempts+1, last_error=?, next_try=? WHERE id=?",
                (error[:500], time.time() + retry_in, vid),
            )

    async def trash_batch(self, limit: int = 100) -> list[int]:
        rows = await self._all("SELECT msg_id FROM trash LIMIT ?", (limit,))
        return [r[0] for r in rows]

    async def trash_done(self, ids: list[int]) -> None:
        async with self.tx() as db:
            await db.executemany("DELETE FROM trash WHERE msg_id=?", [(i,) for i in ids])

    async def add_trash(self, ids: list[int]) -> None:
        async with self.tx() as db:
            await db.executemany("INSERT OR IGNORE INTO trash(msg_id) VALUES(?)", [(i,) for i in ids])

    async def staging_paths(self) -> set[str]:
        rows = await self._all("SELECT staging_path FROM versions WHERE staging_path IS NOT NULL")
        return {r[0] for r in rows}

    async def known_version_ids(self) -> set[int]:
        return {r[0] for r in await self._all("SELECT id FROM versions")}
