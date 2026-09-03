import aiosqlite
import json
from ftp.server import AbstractUserManager, User, AvailableConnections
from ftp.pathio import AbstractPathIO, Node, MongoDBMemoryIO, PathIOError, universal_exception
from pathlib import PurePosixPath
from collections import namedtuple
import unicodedata
import os
import asyncio
from uuid import uuid4
import time

class SQLiteUserManager(AbstractUserManager):
    def __init__(self, db_path):
        self.db_path = db_path
        self.available_connections = {}
        self.users = []

    async def _get_user_dict(self, login):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE login = ?", (login,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                # Row format: id, login, password, permissions (json)
                return {
                    "login": row[1],
                    "password": row[2],
                    "permissions": json.loads(row[3]) if row[3] else []
                }

    async def get_user(self, login):
        user_dict = await self._get_user_dict(login)
        user = User.from_dict(user_dict) if user_dict else None

        if user:
            u = [usr for usr in self.users if usr.login == user.login]
            if u:
                user = u[0].update(user)
            else:
                self.users.append(user)
            if user.login not in self.available_connections:
                self.available_connections[user] = AvailableConnections(100)

        if not user:
            state, info = AbstractUserManager.GetUserResponse.ERROR, "no such username"
        elif self.available_connections[user].locked():
            state, info = AbstractUserManager.GetUserResponse.ERROR, f"too much connections"
        else:
            state, info = AbstractUserManager.GetUserResponse.PASSWORD_REQUIRED, "password required"

        if state != AbstractUserManager.GetUserResponse.ERROR:
            self.available_connections[user].acquire()

        return state, user, info

    async def authenticate(self, user, password):
        return user.password == password

    async def notify_logout(self, user):
        if user in self.available_connections:
            self.available_connections[user].release()


class SQLiteMemoryIO(MongoDBMemoryIO):
    def __init__(self, node, mode, tg, db_path):
        # We don't use the db in MongoDBMemoryIO itself except for replace_one, which we override
        super().__init__(node, mode, tg, None)
        self.db_path = db_path

    async def _update_db(self, name, parent, doc_cache):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if exists
                async with db.execute("SELECT id FROM files WHERE name = ? AND parent = ?", (name, parent)) as cursor:
                    row = await cursor.fetchone()

                parts_json = json.dumps(doc_cache.get("parts", []))

                if row:
                    await db.execute(
                        "UPDATE files SET type = ?, size = ?, status = ?, local_path = ?, mtime = ?, ctime = ?, parts = ? WHERE id = ?",
                        (doc_cache["type"], doc_cache["size"], doc_cache["status"], doc_cache.get("local_path", ""), doc_cache["mtime"], doc_cache["ctime"], parts_json, row[0])
                    )
                else:
                    await db.execute(
                        "INSERT INTO files (type, name, parent, size, status, local_path, mtime, ctime, parts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (doc_cache["type"], name, parent, doc_cache["size"], doc_cache["status"], doc_cache.get("local_path", ""), doc_cache["mtime"], doc_cache["ctime"], parts_json)
                    )
                await db.commit()
        except Exception as e:
            pass

    async def write_stream(self, stream):
        # Temporarily set _db to an object with files.replace_one just to satisfy super().write_stream?
        # Actually it's cleaner to copy the write_stream and adapt, but we want to avoid code duplication.
        # super().write_stream uses self._db.files.replace_one. Let's mock it for SQLite!
        class MockDB:
            class MockFiles:
                async def replace_one(self, query, doc_cache, upsert=True):
                    name = query["name"]
                    parent = query["parent"]
                    await self.parent_obj._update_db(name, parent, doc_cache)
            def __init__(self, parent_obj):
                self.files = self.MockFiles()
                self.files.parent_obj = parent_obj

        self._db = MockDB(self)
        await super().write_stream(stream)


class SQLitePathIO(AbstractPathIO):
    db_path = None
    tg = None
    _memory_cache = {}
    _cache_lock = asyncio.Lock()
    Stats = namedtuple("Stats", ("st_size", "st_ctime", "st_mtime", "st_nlink", "st_mode"))

    def __init__(self, *args, state=None, cwd=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cwd = PurePosixPath("/")

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

    async def _get_file_dict(self, name, parent):
        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM files WHERE name = ? AND parent = ?", (name, parent)) as cursor:
                row = await cursor.fetchone()
                if row:
                    d = dict(row)
                    if d.get("parts"):
                        d["parts"] = json.loads(d["parts"])
                    else:
                        d["parts"] = []
                    return d
                return None

    async def get_node(self, path):
        if str(path) in ("/", "."): return Node("dir", "", 0, 0, size=0, parent="/")
        parent, name = self._split_path(path)
        cache_key = f"{parent}::{name}"

        async with self._cache_lock:
            if cache_key in self._memory_cache:
                return Node(**self._memory_cache[cache_key])

        node = await self._get_file_dict(name, parent)
        if node:
            async with self._cache_lock: self._memory_cache[cache_key] = node
            return Node(**node)

        if parent.startswith("/") and parent != "/":
            alt = parent[1:]
            node = await self._get_file_dict(name, alt)
            if node:
                async with self._cache_lock: self._memory_cache[cache_key] = node
                return Node(**node)
        return None

    @universal_exception
    async def exists(self, path): return (await self.get_node(self._absolute(path))) is not None

    @universal_exception
    async def is_dir(self, path):
        node = await self.get_node(self._absolute(path))
        return node.type == "dir" if node else False

    @universal_exception
    async def is_file(self, path):
        node = await self.get_node(self._absolute(path))
        return node.type == "file" if node else False

    @universal_exception
    async def stat(self, path):
        node = await self.get_node(self._absolute(path))
        if not node: raise FileNotFoundError(f"No such file or directory: {path}")
        mode = 0o40777 if node.type == "dir" else 0o100777
        return SQLitePathIO.Stats(node.size, node.ctime, node.mtime, 1, mode)

    @universal_exception
    async def listdir(self, path):
        path_str = self._sanitize(self._absolute(path).as_posix())
        if not path_str.startswith("/"): path_str = "/" + path_str
        if path_str != "/" and path_str.endswith("/"): path_str = path_str[:-1]

        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            async with db.execute("SELECT name FROM files WHERE parent = ?", (path_str,)) as cursor:
                rows = await cursor.fetchall()
                names = [r[0] for r in rows]

        if path_str.startswith("/") and path_str != "/":
            alt = path_str[1:]
            async with aiosqlite.connect(SQLitePathIO.db_path) as db:
                async with db.execute("SELECT name FROM files WHERE parent = ?", (alt,)) as cursor:
                    rows = await cursor.fetchall()
                    names.extend([r[0] for r in rows if r[0] not in names])

        return names

    @universal_exception
    async def rename(self, source, destination):
        s_parent, s_name = self._split_path(self._absolute(source))
        d_parent, d_name = self._split_path(self._absolute(destination))

        cache_key_s = f"{s_parent}::{s_name}"
        cache_key_d = f"{d_parent}::{d_name}"

        node = await self.get_node(self._absolute(source))
        if not node: raise FileNotFoundError(f"Source not found: {source}")

        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            await db.execute(
                "UPDATE files SET name = ?, parent = ? WHERE name = ? AND parent = ?",
                (d_name, d_parent, s_name, s_parent)
            )

            if node.type == "dir":
                old_prefix = self._sanitize(self._absolute(source).as_posix())
                new_prefix = self._sanitize(self._absolute(destination).as_posix())

                # To match exactly old_prefix or old_prefix/*, but NOT old_prefix_something
                # since we are checking parent path
                # e.g. old_prefix is "/a", we want to match parent = "/a" or parent LIKE "/a/%"
                async with db.execute("SELECT id, parent FROM files WHERE parent = ? OR parent LIKE ?", (old_prefix, f"{old_prefix}/%")) as cursor:
                    rows = await cursor.fetchall()
                    for r in rows:
                        # Replace only if it matches old_prefix exactly at start
                        new_parent = r[1].replace(old_prefix, new_prefix, 1)
                        await db.execute("UPDATE files SET parent = ? WHERE id = ?", (new_parent, r[0]))

            await db.commit()

        async with self._cache_lock:
            if cache_key_s in self._memory_cache:
                doc = self._memory_cache.pop(cache_key_s)
                doc["name"] = d_name
                doc["parent"] = d_parent
                self._memory_cache[cache_key_d] = doc

    @universal_exception
    async def remove(self, path):
        parent, name = self._split_path(self._absolute(path))
        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            await db.execute("DELETE FROM files WHERE name = ? AND parent = ?", (name, parent))
            await db.commit()

        cache_key = f"{parent}::{name}"
        async with self._cache_lock:
            self._memory_cache.pop(cache_key, None)

    @universal_exception
    async def rmdir(self, path):
        parent, name = self._split_path(self._absolute(path))
        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            await db.execute("DELETE FROM files WHERE name = ? AND parent = ?", (name, parent))
            await db.commit()

        cache_key = f"{parent}::{name}"
        async with self._cache_lock:
            self._memory_cache.pop(cache_key, None)

    @universal_exception
    async def mkdir(self, path):
        parent, name = self._split_path(self._absolute(path))
        now = int(time.time())
        doc = {
            "type": "dir", "name": name, "parent": parent, "size": 0,
            "status": "active", "mtime": now, "ctime": now, "parts": []
        }

        async with aiosqlite.connect(SQLitePathIO.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO files (type, name, parent, size, status, mtime, ctime, parts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (doc["type"], name, parent, doc["size"], doc["status"], doc["mtime"], doc["ctime"], "[]")
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                pass # Already exists

        cache_key = f"{parent}::{name}"
        async with self._cache_lock:
            self._memory_cache[cache_key] = doc

    @universal_exception
    async def open(self, path, mode):
        p = self._absolute(path)
        node = await self.get_node(p)
        if mode.startswith("r") and not node: raise FileNotFoundError(f"No such file: {path}")
        if not node:
            parent, name = self._split_path(p)
            node = Node("file", name, parent=parent)
        return SQLiteMemoryIO(node, mode, SQLitePathIO.tg, SQLitePathIO.db_path)
