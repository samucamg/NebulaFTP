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
from pyrogram.errors import FloodWait, RPCError

# Imports locais
from ftp import Server, MongoDBUserManager, MongoDBPathIO
from ftp.common import UPLOAD_QUEUE
from multi_bot import MultiBotManager

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

async def enqueue_staged_files(mongo):
    """Recupera arquivos que ficaram no limbo (staging) após um restart"""
    logger.info("🔍 Verificando arquivos pendentes em staging...")
    try:
        # Busca arquivos marcados como 'staging' ou que tenham local_path
        staged = await mongo.files.find({
            "$or": [
                {"status": "staging"},
                {"local_path": {"$exists": True}, "status": {"$ne": "completed"}}
            ]
        }).to_list(None)
        
        if not staged:
            logger.info("✅ Nenhum arquivo pendente encontrado.")
            return

        logger.info(f"📦 Encontrados {len(staged)} arquivos pendentes.")
        enqueued = 0
        
        for doc in staged:
            filename = doc.get("name", "")
            
            # 🛑 BLOQUEIO CRÍTICO: Ignora parciais do Rclone na recuperação
            if filename.endswith(".partial"):
                continue

            local_path = doc.get("local_path")
            
            # Validação de existência física
            if not local_path or not os.path.exists(local_path):
                # Se não é partial e sumiu, avisa
                logger.warning(f"⚠️ Arquivo físico sumiu: {filename}")
                continue
            
            real_size = os.path.getsize(local_path)
            if real_size == 0: continue

            await UPLOAD_QUEUE.put({
                "path": local_path,
                "filename": filename,
                "parent": doc["parent"],
                "size": real_size
            })
            enqueued += 1
            logger.info(f"📤 Recuperado e Enfileirado: {filename}")
            
        logger.info(f"✅ Recuperação concluída: {enqueued} arquivos reiniciados.")
            
    except Exception as e:
        logger.error(f"❌ Erro na recuperação de staging: {e}")

async def upload_worker(bot_manager, mongo, worker_id):
    logger.info(f"👷 Worker #{worker_id} Pronto")
    # Pega IDs atualizados
    chat_id = bot_manager.target_chat_id 
    backup_id = bot_manager.backup_chat_id
    
    while True:
        try: task = await asyncio.wait_for(UPLOAD_QUEUE.get(), timeout=2.0)
        except asyncio.TimeoutError: continue
            
        local_path = task["path"]; filename = task["filename"]; parent = task["parent"]
        
        # 🛑 PROTEÇÃO DUPLA: Garante que partials não sejam processados
        if filename.endswith(".partial"):
            logger.info(f"⏭️ Ignorando upload parcial: {filename}")
            UPLOAD_QUEUE.task_done()
            continue

        try:
            if not os.path.exists(local_path): UPLOAD_QUEUE.task_done(); continue
            await asyncio.sleep(1)
            real_size = os.path.getsize(local_path)
            if real_size == 0:
                try: os.remove(local_path)
                except: pass
                UPLOAD_QUEUE.task_done(); continue

            logger.info(f"⬆️ [W{worker_id}] Processando: {filename} ({real_size/1024/1024:.2f} MB)")
            
            file_doc = await mongo.files.find_one({"name": filename, "parent": parent})
            if not file_doc:
                logger.warning(f"⚠️ [W{worker_id}] Metadados sumiram: {filename}")
                try: os.remove(local_path)
                except: pass
                UPLOAD_QUEUE.task_done(); continue

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
                                sent_msg = await bot_manager.send_document(
                                    chat_id=chat_id,
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

                        if backup_id:
                            try: await sent_msg.copy(backup_id)
                            except: pass

                        parts_metadata.append({
                            "part_id": part_num, "tg_file": sent_msg.document.file_id,
                            "tg_message": sent_msg.id, "file_size": len(chunk_data),
                            "chunk_name": chunk_name
                        })
                        part_num += 1; await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"❌ [W{worker_id}] Abortado: {filename}: {e}"); upload_failed = True; Metrics.log_fail()

            if not upload_failed:
                await mongo.files.update_one(
                    {"_id": file_doc["_id"]},
                    {"$set": {"size": real_size, "uploaded_at": int(time.time()), "parts": parts_metadata, "obfuscated_id": file_uuid, "status": "completed"}, "$unset": {"uploadId": 1, "local_path": 1}}
                )
                logger.info(f"✅ [W{worker_id}] Concluído: {filename}")
                Metrics.log_success(real_size)
                try: os.remove(local_path)
                except: pass
            
        except Exception as e: logger.error(f"❌ [W{worker_id}] Crítico: {e}")
        finally: UPLOAD_QUEUE.task_done()

async def resolve_channels(bot_manager):
    raw_chat = environ.get("CHAT_ID")
    raw_backup = environ.get("BACKUP_CHAT_ID")
    target_chat = int(raw_chat) if raw_chat.lstrip("-").isdigit() else raw_chat
    target_backup = int(raw_backup) if raw_backup and raw_backup.lstrip("-").isdigit() else raw_backup

    logger.info("🔍 Verificando acesso aos canais...")
    bot = bot_manager.clients[0]
    
    try:
        chat = await bot.get_chat(target_chat)
        logger.info(f"✅ Canal Principal Confirmado: {chat.title} (ID: {chat.id})")
        try:
            msg = await bot.send_message(chat.id, "🔄 Nebula FTP Conectado", disable_notification=True)
        except Exception as e:
            logger.critical(f"❌ Bot sem permissão de escrita! Erro: {e}"); return False
        bot_manager.target_chat_id = chat.id
    except Exception as e:
        logger.critical(f"❌ Canal principal inválido '{target_chat}': {e}"); return False

    if target_backup:
        try:
            chat = await bot.get_chat(target_backup)
            logger.info(f"🛡️ Canal Backup Confirmado: {chat.title} (ID: {chat.id})")
            bot_manager.backup_chat_id = chat.id
        except:
            logger.warning(f"⚠️ Canal Backup falhou (ignorado)."); bot_manager.backup_chat_id = None
    else: bot_manager.backup_chat_id = None
    return True

async def main():
    api_id = int(environ.get("API_ID"))
    api_hash = environ.get("API_HASH")
    tokens = [t.strip() for t in (environ.get("BOT_TOKENS") or environ.get("BOT_TOKEN")).split(",") if t.strip()]

    if not tokens: logger.critical("❌ Sem tokens!"); return

    bot_manager = MultiBotManager()
    logger.info(f"🤖 Inicializando {len(tokens)} bots...")
    
    for i, token in enumerate(tokens):
        sname = f"FTP_Bot_{i+1}" if i > 0 else "FTP_Bot"
        try: await bot_manager.add_bot(sname, api_id, api_hash, token)
        except Exception as e: logger.error(f"❌ Falha bot {i+1}: {e}")

    if not bot_manager.clients: logger.critical("❌ Abortando."); return
    bot_manager.finalize_setup()
    
    if not await resolve_channels(bot_manager): return

    loop = asyncio.get_event_loop()
    try:
        # Usa Write Concern Majority para consistência
        mongo = AsyncIOMotorClient(environ.get("MONGODB"), io_loop=loop, w="majority").ftp
        await setup_database_indexes(mongo)
    except Exception as e: logger.critical(f"❌ Erro DB: {e}"); return
    
    MongoDBPathIO.db = mongo
    MongoDBPathIO.tg = bot_manager
    server = Server(MongoDBUserManager(mongo), MongoDBPathIO)
    
    # ✅ 1. Recupera arquivos pendentes
    await enqueue_staged_files(mongo)
    
    # ✅ 2. Inicia Workers
    for i in range(MAX_WORKERS): asyncio.create_task(upload_worker(bot_manager, mongo, i+1))
    
    asyncio.create_task(garbage_collector())
    asyncio.create_task(stats_reporter())
    
    port = int(environ.get("PORT", 2121))
    logger.info(f"🚀 Nebula FTP v2.3 Rodando na porta {port}")
    logger.info(f"   ⚙️ Config: {MAX_WORKERS} workers | {CHUNK_SIZE_MB}MB chunks | {MAX_RETRIES} retries")
    
    ftp_server_task = asyncio.create_task(server.run(environ.get("HOST", "0.0.0.0"), port))
    
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop_event.set)
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    
    try: await stop_event.wait()
    except CancelledError: pass
    finally:
        logger.info("⏳ Shutdown: Aguardando uploads (30s)...")
        try:
            if not UPLOAD_QUEUE.empty(): await asyncio.wait_for(UPLOAD_QUEUE.join(), timeout=30)
        except: logger.warning("⚠️ Timeout no shutdown.")
        await server.close()
        for client in bot_manager.clients: await client.stop()
        logger.info("👋 Desligado.")

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
