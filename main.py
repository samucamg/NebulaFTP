# main.py - NEBULA FTP LIGHT (Single Bot)
import asyncio
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
from ftp.common import UPLOAD_QUEUE

if exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

# --- CONFIGURAÇÃO ---
LOG_LEVEL = environ.get("LOG_LEVEL", "INFO")
CHUNK_SIZE_MB = int(environ.get("CHUNK_SIZE_MB", 64))
CHUNK_SIZE = CHUNK_SIZE_MB * 1024 * 1024 
MAX_RETRIES = int(environ.get("MAX_RETRIES", 5))
MAX_STAGING_AGE = int(environ.get("MAX_STAGING_AGE", 3600))
MAX_WORKERS = int(environ.get("MAX_WORKERS", 4))

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
        await mongo.files.create_index("status") 
        logger.info("✅ Índices verificados.")
    except Exception as e: logger.warning(f"⚠️ Aviso índices: {e}")

async def garbage_collector():
    logger.info(f"🧹 Garbage Collector Iniciado (Max Age: {MAX_STAGING_AGE}s)")
    staging_dir = "staging"
    while True:
        try:
            now = time.time()
            if os.path.exists(staging_dir):
                for f in os.listdir(staging_dir):
                    fp = os.path.join(staging_dir, f)
                    if os.path.isfile(fp):
                        if now - os.path.getmtime(fp) > MAX_STAGING_AGE:
                            try: os.remove(fp); logger.warning(f"🧹 GC: Lixo removido: {f}")
                            except Exception as e: logger.error(f"❌ GC Erro {f}: {e}")
        except Exception as e: logger.error(f"❌ GC Falha Geral: {e}")
        await asyncio.sleep(600)

async def upload_worker(bot, mongo, chat_id, worker_id):
    """Worker simplificado - Single Bot"""
    logger.info(f"👷 Worker #{worker_id} Pronto")
    
    while True:
        try: 
            task = await asyncio.wait_for(UPLOAD_QUEUE.get(), timeout=2.0)
        except asyncio.TimeoutError: 
            continue
            
        local_path = task["path"]
        filename = task["filename"]
        parent = task["parent"]
        
        if filename.endswith(".partial"):
            logger.info(f"⏭️ Ignorando upload parcial: {filename}")
            UPLOAD_QUEUE.task_done()
            continue

        try:
            if not os.path.exists(local_path): 
                UPLOAD_QUEUE.task_done()
                continue
                
            real_size = os.path.getsize(local_path)
            if real_size == 0:
                try: os.remove(local_path)
                except: pass
                UPLOAD_QUEUE.task_done()
                continue

            logger.info(f"⬆️ [W{worker_id}] Processando: {filename} ({real_size/1024/1024:.2f} MB)")
            
            file_doc = await mongo.files.find_one({"name": filename, "parent": parent})
            if not file_doc:
                logger.warning(f"⚠️ [W{worker_id}] Metadados sumiram: {filename}")
                UPLOAD_QUEUE.task_done()
                continue

            file_uuid = str(uuid.uuid4())
            parts_metadata = []
            
            async with aiofiles.open(local_path, "rb") as f:
                part_num = 0
                while True:
                    chunk_data = await f.read(CHUNK_SIZE)
                    if not chunk_data: break
                    
                    chunk_name = f"{file_uuid}.part_{part_num:03d}"
                    mem_file = io.BytesIO(chunk_data)
                    mem_file.name = chunk_name 
                    
                    for attempt in range(1, MAX_RETRIES + 1):
                        try:
                            mem_file.seek(0)
                            sent_msg = await bot.send_document(
                                chat_id=chat_id,
                                document=mem_file,
                                file_name=chunk_name,
                                force_document=True,
                                caption=""
                            )
                            break 
                        except FloodWait as e:
                            await asyncio.sleep(e.value + 2)
                        except Exception as e:
                            logger.error(f"❌ [W{worker_id}] Erro ({attempt}): {e}")
                            await asyncio.sleep(2 ** attempt)
                    
                    parts_metadata.append({
                        "part_id": part_num,
                        "tg_file": sent_msg.document.file_id,
                        "tg_message": sent_msg.id,
                        "file_size": len(chunk_data),
                        "chunk_name": chunk_name
                    })
                    part_num += 1

            await mongo.files.update_one(
                {"_id": file_doc["_id"]},
                {
                    "$set": {
                        "size": real_size,
                        "uploaded_at": int(time.time()),
                        "parts": parts_metadata,
                        "obfuscated_id": file_uuid,
                        "status": "completed"
                    },
                    "$unset": {"local_path": 1}
                }
            )
            
            logger.info(f"✅ [W{worker_id}] Concluído: {filename}")
            Metrics.log_success(real_size)
            
            try: os.remove(local_path)
            except: pass
            
        except Exception as e:
            logger.error(f"❌ [W{worker_id}] Crítico: {e}")
            Metrics.log_fail()
        finally:
            UPLOAD_QUEUE.task_done()

async def main():
    api_id = int(environ.get("API_ID"))
    api_hash = environ.get("API_HASH")
    bot_token = environ.get("BOT_TOKEN")  # ⚠️ Mudança: BOT_TOKEN no singular
    chat_id = int(environ.get("CHAT_ID"))

    if not bot_token:
        logger.critical("❌ BOT_TOKEN não configurado!")
        return

    # Inicializa bot único
    logger.info("🤖 Inicializando bot...")
    bot = Client("FTP_Bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
    
    await bot.start()
    logger.info("✅ Bot conectado!")
    
    # Verifica canal
    try:
        chat = await bot.get_chat(chat_id)
        logger.info(f"✅ Canal Confirmado: {chat.title} (ID: {chat_id})")
    except Exception as e:
        logger.critical(f"❌ Erro ao acessar canal: {e}")
        return

    # MongoDB
    loop = asyncio.get_event_loop()
    mongo = AsyncIOMotorClient(environ.get("MONGODB"), io_loop=loop, w="majority").ftp
    await setup_database_indexes(mongo)
    
    # Configura PathIO
    MongoDBPathIO.db = mongo
    MongoDBPathIO.tg = bot  # ⚠️ Passa o bot direto, não um manager
    
    server = Server(MongoDBUserManager(mongo), MongoDBPathIO)
    
    # Inicia workers
    for i in range(MAX_WORKERS):
        asyncio.create_task(upload_worker(bot, mongo, chat_id, i+1))
    
    asyncio.create_task(garbage_collector())
    asyncio.create_task(stats_reporter())
    
    port = int(environ.get("PORT", 2121))
    logger.info(f"🚀 Nebula FTP Community Edition v1.0")
    logger.info(f"   ⚙️ {MAX_WORKERS} workers | {CHUNK_SIZE_MB}MB chunks")
    logger.info(f"   🌐 Servidor rodando na porta {port}")
    
    ftp_server_task = asyncio.create_task(server.run(environ.get("HOST", "0.0.0.0"), port))
    
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    
    try:
        await stop_event.wait()
    except:
        pass
    finally:
        logger.info("⏳ Shutdown...")
        await server.close()
        await bot.stop()
        logger.info("👋 Desligado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
