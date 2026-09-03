import aiosqlite
import json
import asyncio

class SQLiteCursor:
    def __init__(self, query_coro):
        self._query_coro = query_coro
        self._cursor = None
        self._rows = None
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._rows is None:
            self._rows = await self._query_coro()

        if self._idx < len(self._rows):
            row = self._rows[self._idx]
            self._idx += 1
            return row
        else:
            raise StopAsyncIteration

class SQLiteCollection:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name

    def _build_where(self, filter):
        if not filter:
            return "", []

        clauses = []
        params = []
        for k, v in filter.items():
            if k == '_id': continue # Skip MongoDB specific _id
            if isinstance(v, dict):
                # Basic mock for regex and other operators
                if '$regex' in v:
                    clauses.append(f"{k} LIKE ?")
                    # simple conversion from regex to LIKE
                    val = v['$regex']
                    if val.startswith('^'): val = val[1:]
                    else: val = '%' + val
                    if val.endswith('$'): val = val[:-1]
                    else: val = val + '%'
                    params.append(val)
                elif '$not' in v:
                    not_v = v['$not']
                    if isinstance(not_v, dict) and '$regex' in not_v:
                        clauses.append(f"{k} NOT LIKE ?")
                        val = not_v['$regex']
                        if val.startswith('^'): val = val[1:]
                        else: val = '%' + val
                        if val.endswith('$'): val = val[:-1]
                        else: val = val + '%'
                        params.append(val)
            else:
                clauses.append(f"json_extract(data, '$.{k}') = ?")
                params.append(v)

        if not clauses:
            return "", []
        return "WHERE " + " AND ".join(clauses), params

    async def find_one(self, filter):
        where, params = self._build_where(filter)
        query = f"SELECT data FROM {self.table_name} {where} LIMIT 1"
        async with self.db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                data = json.loads(row[0])
                data['_id'] = str(data.get('login') or data.get('name', '')) # mock _id
                return data
            return None

    def find(self, filter):
        where, params = self._build_where(filter)
        query = f"SELECT data FROM {self.table_name} {where}"

        async def do_query():
            async with self.db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for r in rows:
                    data = json.loads(r[0])
                    data['_id'] = str(data.get('login') or data.get('name', ''))
                    results.append(data)
                return results

        return SQLiteCursor(do_query)

    async def insert_one(self, document):
        if '_id' in document:
            document = document.copy()
            del document['_id']

        if 'login' in document:
            await self._ensure_users_table()
            query = "INSERT INTO users (login, data) VALUES (?, ?)"
            await self.db.execute(query, (document.get('login', ''), json.dumps(document)))
        else:
            await self._ensure_files_table()
            query = "INSERT INTO files (name, parent, data) VALUES (?, ?, ?)"
            await self.db.execute(query, (document.get('name', ''), document.get('parent', ''), json.dumps(document)))
        await self.db.commit()

    async def update_one(self, filter, update, upsert=False):
        doc = await self.find_one(filter)
        if doc is None:
            if upsert:
                # Basic upsert implementation - very limited logic
                if '$setOnInsert' in update:
                    new_doc = {**filter, **update['$setOnInsert']}
                elif '$set' in update:
                    new_doc = {**filter, **update['$set']}
                else:
                    new_doc = {**filter}
                await self.insert_one(new_doc)
            return

        if '$set' in update:
            for k, v in update['$set'].items():
                doc[k] = v
        if '$unset' in update:
            for k in update['$unset'].keys():
                doc.pop(k, None)
        if '$push' in update:
            for k, v in update['$push'].items():
                if k not in doc: doc[k] = []
                doc[k].append(v)
        if '$pull' in update:
            for k, v in update['$pull'].items():
                if k in doc and isinstance(doc[k], list):
                    # Simple equality pull check
                    new_list = []
                    for item in doc[k]:
                        if isinstance(item, dict) and isinstance(v, dict):
                            # Dict equality
                            match = True
                            for vk, vv in v.items():
                                if item.get(vk) != vv:
                                    match = False
                                    break
                            if not match:
                                new_list.append(item)
                        elif item != v:
                            new_list.append(item)
                    doc[k] = new_list

        where, params = self._build_where(filter)

        # We assume _id or combination of name+parent is unique for updates
        query = f"UPDATE {self.table_name} SET data = ? {where}"
        await self.db.execute(query, [json.dumps(doc)] + params)
        await self.db.commit()

    async def replace_one(self, filter, replacement, upsert=False):
        doc = await self.find_one(filter)
        if doc is None:
            if upsert:
                await self.insert_one({**filter, **replacement})
            return

        where, params = self._build_where(filter)
        query = f"UPDATE {self.table_name} SET data = ? {where}"

        if '_id' in replacement:
            replacement = replacement.copy()
            del replacement['_id']

        await self.db.execute(query, [json.dumps(replacement)] + params)
        await self.db.commit()

    async def delete_one(self, filter):
        where, params = self._build_where(filter)
        query = f"DELETE FROM {self.table_name} {where}"
        await self.db.execute(query, params)
        await self.db.commit()

    async def delete_many(self, filter):
        where, params = self._build_where(filter)
        query = f"DELETE FROM {self.table_name} {where}"
        await self.db.execute(query, params)
        await self.db.commit()

    async def create_index(self, keys, **kwargs):
        # Index creation mock. In SQLite, we handle this during table creation.
        pass

    async def _ensure_users_table(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                login TEXT PRIMARY KEY,
                data TEXT
            )
        """)

    async def _ensure_files_table(self):
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                parent TEXT,
                data TEXT,
                UNIQUE(name, parent)
            )
        """)
        await self.db.execute("CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent)")

class MotorMock:
    def __init__(self, db_path):
        self.db_path = db_path
        if self.db_path.startswith('sqlite://'):
            self.db_path = self.db_path[9:]
        self.db = None

    async def _connect(self):
        if self.db is None:
            self.db = await aiosqlite.connect(self.db_path)
            # Create tables
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    login TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    parent TEXT,
                    data TEXT,
                    UNIQUE(name, parent)
                )
            """)
            await self.db.execute("CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent)")
            await self.db.commit()

            self.users = SQLiteCollection(self.db, "users")
            self.files = SQLiteCollection(self.db, "files")
            self.ftp = self # mock for `mongo.ftp` returning itself

    # Mock AsyncIOMotorClient behaviour which returns MotorDatabase using property access
    def __getattr__(self, name):
        if name in ['users', 'files', 'ftp']:
            return getattr(self, name) if hasattr(self, name) else self
        raise AttributeError(f"'MotorMock' object has no attribute '{name}'")

async def get_db_client(uri):
    if uri.startswith('sqlite://'):
        mock = MotorMock(uri)
        await mock._connect()
        return mock
    else:
        from motor.motor_asyncio import AsyncIOMotorClient
        loop = asyncio.get_event_loop()
        return AsyncIOMotorClient(uri, io_loop=loop, w="majority")
