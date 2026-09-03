import asyncio
import aiosqlite
import json
import os
import time
import logging
import uuid
import io
import aiofiles
import signal
from logging.handlers import RotatingFileHandler
from os import environ
from os.path import exists
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

# Imports locais
from ftp import Server, MongoDBUserManager, MongoDBPathIO
import json
from ftp.sqlite_db import SQLiteUserManager, SQLitePathIO
from ftp.common import UPLOAD_QUEUE
import json
from ftp.sftp import start_sftp_server
from ftp.pathio import PathIONursery
from web import start_web_server

if exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

# --- CARREGAMENTO DE CONFIGURAÇÕES DO .ENV ---
LOG_LEVEL = environ.get("LOG_LEVEL", "INFO")
CHUNK_SIZE_MB = int(environ.get("CHUNK_SIZE_MB", 64))
CHUNK_SIZE = CHUNK_SIZE_MB * 1024 * 1024
MAX_RETRIES = int(environ.get("MAX_RETRIES", 5))
MAX_STAGING_AGE = int(environ.get("MAX_STAGING_AGE", 3600))
MAX_WORKERS = int(environ.get("MAX_WORKERS", 4))

# Portas Passivas
PASSIVE_PORTS = None
pp_str = environ.get("PASSIVE_PORTS")
if pp_str and "-" in pp_str:
    try:
        start_p, end_p = map(int, pp_str.split("-"))
        PASSIVE_PORTS = range(start_p, end_p + 1)
    except: pass

# --- CONTROLE DE LOCKS (PROTEÇÃO) ---
# Conjunto para armazenar caminhos de arquivos que estão sendo enviados agora.
# O Garbage Collector NÃO pode tocar nestes arquivos.
ACTIVE_UPLOADS = set()

# --- LOGGING ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('nebula.log', maxBytes=5*1024*1024, backupCount=2)
log_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger = logging.getLogger("NebulaFTP")
logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger.addHandler(log_handler)
logger.addHandler(console_handler)

# --- MÉTRICAS ---
class Metrics:
    uploads_total = 0; uploads_failed = 0; bytes_uploaded = 0
    @classmethod
    def log_success(cls, size): cls.uploads_total += 1; cls.bytes_uploaded += size
    @classmethod
    def log_fail(cls): cls.uploads_failed += 1
    @classmethod
    def report(cls):
        mb = cls.bytes_uploaded / (1024*1024)
        logger.info(f"📊 Stats: ⬆️ {cls.uploads_total} uploads ({mb:.2f} MB) | ❌ {cls.uploads_failed} falhas")

async def stats_reporter():
    while True: await asyncio.sleep(300); Metrics.report()

async def setup_database_indexes(mongo):
    logger.info("🔧 Verificando índices do Banco de Dados...")
    try:
        await mongo.files.create_index([("parent", 1), ("name", 1)], unique=True)
        await mongo.files.create_index("parent")
        await mongo.files.create_index("uploadId", sparse=True)
        await mongo.files.create_index("uploaded_at")
        await mongo.files.create_index("status")
        logger.info("✅ Índices verificados.")
    except Exception as e: logger.warning(f"⚠️ Aviso índices: {e}")

async def setup_sqlite_tables(db_path):
    logger.info("🔧 Verificando tabelas SQLite...")
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE,
                password TEXT,
                permissions TEXT
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                name TEXT,
                parent TEXT,
                size INTEGER,
                status TEXT,
                local_path TEXT,
                mtime INTEGER,
                ctime INTEGER,
                parts TEXT
            )''')
            await db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_parent_name ON files(parent, name)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_parent ON files(parent)')
            await db.commit()

            # Create a default user if none exists
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                if row[0] == 0:
                    default_perms = json.dumps([{"path": "/", "readable": True, "writable": True}])
                    await db.execute(
                        "INSERT INTO users (login, password, permissions) VALUES (?, ?, ?)",
                        ("admin", "admin", default_perms)
                    )
                    await db.commit()
                    logger.info("✅ Usuário padrão (admin/admin) criado no SQLite.")

        logger.info("✅ Tabelas SQLite verificadas.")
    except Exception as e: logger.warning(f"⚠️ Aviso tabelas SQLite: {e}")

async def garbage_collector():
    logger.info(f"🧹 Garbage Collector Iniciado (Max Age: {MAX_STAGING_AGE}s)")
    staging_dir = "staging"
    while True:
        try:
            now = time.time()
            if os.path.exists(staging_dir):
                for root, dirs, files in os.walk(staging_dir):
                    for f in files:
                        if f.endswith(".partial"): continue
                        fp = os.path.join(root, f)

                        # --- PROTEÇÃO CRÍTICA ---
                        # Se o arquivo estiver sendo enviado, PULA.
                        if fp in ACTIVE_UPLOADS:
                            continue
                        # ------------------------

                        if now - os.path.getmtime(fp) > MAX_STAGING_AGE:
                            try:
                                os.remove(fp)
                                logger.warning(f"🧹 GC: Lixo removido: {f}")
                            except Exception as e:
                                logger.error(f"❌ GC Erro {f}: {e}")
        except Exception as e: logger.error(f"❌ GC Falha Geral: {e}")
        await asyncio.sleep(600)

async def folder_watcher(db_wrapper):
    """
    Vigia a pasta 'staging' RECURSIVAMENTE.
    Mapeia arquivos para a PASTA DO UTILIZADOR.
    """
    logger.info("👀 Folder Watcher Iniciado")
    staging_dir = "staging"
    if not os.path.exists(staging_dir): os.makedirs(staging_dir)

    target_root = "/"
    try:
        user = await db_wrapper.get_user()
        if user:
            target_root = f"/{user['login']}"
            logger.info(f"🎯 Modo MonoBot: Arquivos de staging irão para: {target_root}")
        else:
            logger.warning("⚠️ Nenhum utilizador encontrado no DB. Arquivos irão para a Raiz '/'.")
    except Exception as e:
        logger.error(f"❌ Erro ao buscar utilizador: {e}")

    while True:
        try:
            for root, dirs, files in os.walk(staging_dir):
                for f in files:
                    if f.endswith(".partial"): continue
                    fp = os.path.join(root, f)

                    if not os.path.isfile(fp): continue

                    # Ignora se já estiver sendo enviado (evita duplicar na fila)
                    if fp in ACTIVE_UPLOADS: continue

                    size_t1 = os.path.getsize(fp)
                    if size_t1 == 0: continue

                    rel_dir = os.path.relpath(root, staging_dir)

                    if rel_dir == ".":
                        parent_path = target_root
                    else:
                        normalized_rel = rel_dir.replace(os.sep, "/")
                        if target_root == "/": parent_path = f"/{normalized_rel}"
                        else: parent_path = f"{target_root}/{normalized_rel}"

                    doc = await db_wrapper.find_file(f, parent_path)

                    if not doc:
                        await asyncio.sleep(2)
                        if os.path.getsize(fp) != size_t1: continue

                        logger.info(f"👀 Detectado: {f} -> {parent_path}")

                        if parent_path != "/":
                            parts = parent_path.strip("/").split("/")
                            current_parent = "/"
                            for part in parts:
                                if db_wrapper.db_type == "mongodb":
                                    await db_wrapper.db_client.files.update_one(
                                        {"name": part, "parent": current_parent},
                                        {"$setOnInsert": {"type": "dir", "ctime": int(time.time()), "mtime": int(time.time()), "size": 0}},
                                        upsert=True
                                    )
                                else:
                                    async with aiosqlite.connect(db_wrapper.db_path) as conn:
                                        async with conn.execute("SELECT id FROM files WHERE name = ? AND parent = ?", (part, current_parent)) as cursor:
                                            if not await cursor.fetchone():
                                                await conn.execute("INSERT INTO files (type, name, parent, size, status, mtime, ctime, parts) VALUES (?, ?, ?, ?, ?, ?, ?, '[]')", ("dir", part, current_parent, 0, "active", int(time.time()), int(time.time())))
                                                await conn.commit()
                                if current_parent == "/": current_parent = "/" + part
                                else: current_parent = f"{current_parent}/{part}"

                        file_doc = {
                            "type": "file", "name": f, "parent": parent_path, "size": size_t1,
                            "status": "staging", "local_path": fp,
                            "mtime": int(time.time()), "ctime": int(time.time()), "parts": []
                        }

                        try:
                            if db_wrapper.db_type == "mongodb":
                                await db_wrapper.db_client.files.insert_one(file_doc)
                            else:
                                async with aiosqlite.connect(db_wrapper.db_path) as conn:
                                    await conn.execute("INSERT INTO files (type, name, parent, size, status, local_path, mtime, ctime, parts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (file_doc["type"], file_doc["name"], file_doc["parent"], file_doc["size"], file_doc["status"], file_doc["local_path"], file_doc["mtime"], file_doc["ctime"], json.dumps([])))
                                    await conn.commit()
                            await UPLOAD_QUEUE.put({
                                "path": fp, "filename": f, "parent": parent_path, "size": size_t1
                            })
                            logger.info(f"📤 Enfileirado: {f}")
                        except Exception as e:
                            logger.warning(f"⚠️ Erro registro {f}: {e}")

        except Exception as e:
            logger.error(f"❌ Erro Watcher: {e}")

        await asyncio.sleep(5)

class DBWrapper:
    def __init__(self, db_type, db_client=None, db_path=None):
        self.db_type = db_type
        self.db_client = db_client
        self.db_path = db_path

    async def get_user(self):
        if self.db_type == 'mongodb':
            return await self.db_client.users.find_one({})
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users LIMIT 1") as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    async def find_file(self, filename, parent):
        if self.db_type == 'mongodb':
            return await self.db_client.files.find_one({"name": filename, "parent": parent})
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM files WHERE name = ? AND parent = ?", (filename, parent)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        d = dict(row)
                        d["_id"] = d["id"] # Mock _id for compatibility
                        return d
                    return None

    async def update_file(self, file_id, real_size, parts_metadata, file_uuid):
        now = int(time.time())
        if self.db_type == 'mongodb':
            await self.db_client.files.update_one(
                {"_id": file_id},
                {"$set": {"size": real_size, "uploaded_at": now, "parts": parts_metadata, "obfuscated_id": file_uuid, "status": "completed"}, "$unset": {"uploadId": 1, "local_path": 1}}
            )
        else:
            async with aiosqlite.connect(self.db_path) as db:
                parts_json = json.dumps(parts_metadata)
                await db.execute(
                    "UPDATE files SET size = ?, mtime = ?, parts = ?, status = 'completed', local_path = '' WHERE id = ?",
                    (real_size, now, parts_json, file_id)
                )
                await db.commit()


async def upload_worker(bot, target_chat_id, db_wrapper, worker_id):
    logger.info(f"👷 Worker #{worker_id} Pronto")

    while True:
        try: task = await asyncio.wait_for(UPLOAD_QUEUE.get(), timeout=2.0)
        except asyncio.TimeoutError: continue

        local_path = task["path"]; filename = task["filename"]; parent = task["parent"]

        # --- LOCK: Bloqueia o arquivo para o GC não apagar ---
        ACTIVE_UPLOADS.add(local_path)
        # -----------------------------------------------------

        try:
            if filename.endswith(".partial"): continue

            if not os.path.exists(local_path): continue

            real_size = os.path.getsize(local_path)
            if real_size == 0:
                try: os.remove(local_path)
                except: pass
                continue

            logger.info(f"⬆️ [W{worker_id}] Processando: {filename} ({real_size/1024/1024:.2f} MB)")

            file_doc = await db_wrapper.find_file(filename, parent)
            if not file_doc:
                logger.warning(f"⚠️ [W{worker_id}] Metadados não encontrados: {filename}")
                continue

            file_uuid = str(uuid.uuid4())
            parts_metadata = []
            upload_failed = False

            try:
                async with aiofiles.open(local_path, "rb") as f:
                    part_num = 0
                    while True:
                        chunk_data = await f.read(CHUNK_SIZE)
                        if not chunk_data: break

                        chunk_name = f"{file_uuid}.part_{part_num:03d}"
                        mem_file = io.BytesIO(chunk_data); mem_file.name = chunk_name
                        sent_msg = None

                        for attempt in range(1, MAX_RETRIES + 1):
                            try:
                                mem_file.seek(0)
                                sent_msg = await bot.send_document(
                                    chat_id=target_chat_id,
                                    document=mem_file,
                                    file_name=chunk_name,
                                    force_document=True,
                                    caption=""
                                )
                                break
                            except FloodWait as e:
                                w = e.value + 2; logger.warning(f"⏳ [W{worker_id}] FloodWait: {w}s")
                                await asyncio.sleep(w)
                            except RPCError as e:
                                w = (2 ** attempt); logger.error(f"❌ [W{worker_id}] Erro TG ({attempt}): {e}")
                                await asyncio.sleep(w)
                            except Exception as e:
                                logger.error(f"❌ [W{worker_id}] Erro: {e}"); await asyncio.sleep(5)

                        if not sent_msg: raise Exception(f"Falha upload parte {part_num}")

                        parts_metadata.append({
                            "part_id": part_num, "tg_file": sent_msg.document.file_id,
                            "tg_message": sent_msg.id, "file_size": len(chunk_data),
                            "chunk_name": chunk_name
                        })
                        part_num += 1; await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"❌ [W{worker_id}] Abortado: {filename}: {e}"); upload_failed = True; Metrics.log_fail()

            if not upload_failed:
                await db_wrapper.update_file(file_doc["_id"], real_size, parts_metadata, file_uuid)
                logger.info(f"✅ [W{worker_id}] Concluído: {filename}")
                Metrics.log_success(real_size)
                # Agora sim o GC ou nós mesmos podemos remover
                try: os.remove(local_path)
                except: pass

        except Exception as e: logger.error(f"❌ [W{worker_id}] Crítico: {e}")
        finally:
            # --- UNLOCK: Libera o arquivo ---
            ACTIVE_UPLOADS.discard(local_path)
            UPLOAD_QUEUE.task_done()

async def resolve_channel(bot):
    raw_chat = environ.get("CHAT_ID")
    target_chat = int(raw_chat) if raw_chat and raw_chat.lstrip("-").isdigit() else raw_chat

    logger.info("🔍 Verificando acesso ao canal...")
    try:
        async for dialog in bot.get_dialogs(limit=50): pass
    except: pass

    try:
        chat = await bot.get_chat(target_chat)
        logger.info(f"✅ Canal Confirmado: {chat.title} (ID: {chat.id})")
        try: await bot.send_message(chat.id, "🔄 Nebula FTP MonoBot Conectado", disable_notification=True)
        except: pass
        return chat.id
    except Exception as e:
        logger.critical(f"❌ Canal inválido '{target_chat}': {e}"); return None

async def main():
    api_id_str = environ.get("API_ID")
    if not api_id_str:
        logger.critical("❌ API_ID não configurado! Rode setup.py ou edite .env")
        return
    api_id = int(api_id_str)
    api_hash = environ.get("API_HASH")
    token_str = environ.get("BOT_TOKENS") or environ.get("BOT_TOKEN")
    token = token_str.split(",")[0].strip() if token_str else None

    if not token: logger.critical("❌ Sem token!"); return

    bot = Client("Nebula_MonoBot", api_id=api_id, api_hash=api_hash, bot_token=token)
    logger.info("🤖 Iniciando Bot...")
    try: await bot.start()
    except Exception as e: logger.critical(f"❌ Falha ao iniciar bot: {e}"); return

    target_chat_id = await resolve_channel(bot)
    if not target_chat_id: await bot.stop(); return

    loop = asyncio.get_event_loop()

    db_type = environ.get("DB_TYPE", "sqlite").lower()
    mongo = None
    if db_type == "mongodb":
        try:
            mongo = AsyncIOMotorClient(environ.get("MONGODB"), io_loop=loop, w="majority").ftp
            await setup_database_indexes(mongo)
            db_wrapper = DBWrapper("mongodb", db_client=mongo)
            MongoDBPathIO.db = mongo; MongoDBPathIO.tg = bot
            user_manager = MongoDBUserManager(mongo)
            path_io_class = MongoDBPathIO
        except Exception as e:
            logger.critical(f"❌ Erro MongoDB DB: {e}"); return
    else:
        db_path = environ.get("DB_FILE", "nebula.db")
        try:
            await setup_sqlite_tables(db_path)
            db_wrapper = DBWrapper("sqlite", db_path=db_path)
            SQLitePathIO.db_path = db_path; SQLitePathIO.tg = bot
            user_manager = SQLiteUserManager(db_path)
            path_io_class = SQLitePathIO
        except Exception as e:
            logger.critical(f"❌ Erro SQLite DB: {e}"); return

    server = Server(user_manager, path_io_class)
    path_io_nursery = PathIONursery(path_io_class)

    asyncio.create_task(garbage_collector())
    asyncio.create_task(stats_reporter())
    asyncio.create_task(folder_watcher(db_wrapper))

    for i in range(MAX_WORKERS): asyncio.create_task(upload_worker(bot, target_chat_id, db_wrapper, i+1))

    host = environ.get("HOST", "0.0.0.0")
    ftp_port = int(environ.get("PORT", 2121))
    sftp_port = int(environ.get("SFTP_PORT", 2222))
    web_port = int(environ.get("WEB_PORT", 8080))

    logger.info(f"🚀 Iniciando Servidor FTP na porta {ftp_port}")
    ftp_server_task = asyncio.create_task(server.run(host, ftp_port))

    logger.info(f"🚀 Iniciando Servidor SFTP na porta {sftp_port}")
    sftp_server_task = asyncio.create_task(start_sftp_server(user_manager, path_io_nursery, host, sftp_port))

    logger.info(f"🚀 Iniciando Painel Web na porta {web_port}")
    if db_type == "mongodb":
        web_runner = await start_web_server(mongo, web_port, "mongodb")
    else:
        web_runner = await start_web_server(db_path, web_port, "sqlite")

    stop_event = asyncio.Event()
    if os.name == "posix":
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
    if os.name == "posix":
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)

    try: await stop_event.wait()
    except asyncio.CancelledError: pass
    finally:
        logger.info("⏳ Shutdown...")
        try:
            if not UPLOAD_QUEUE.empty(): await asyncio.wait_for(UPLOAD_QUEUE.join(), timeout=30)
        except: pass
        await server.close()
        await web_runner.cleanup()
        await bot.stop()
        logger.info("👋 Desligado.")

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
