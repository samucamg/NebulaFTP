import asyncio
import os
import logging
import sys
import requests
import time
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

# Importações do projeto
from ftp.server import Server, MongoDBUserManager
from ftp.pathio import MongoDBPathIO
from ftp.common import UPLOAD_QUEUE

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("NebulaFTP")

# --- CONFIGURAÇÕES ---
MONGODB_URI = os.getenv("MONGODB", "mongodb://mongo:27017")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 2121))
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID_INPUT = os.getenv("CHANNEL_ID") # Pode ser @canal ou ID numérico

# --- LÓGICA DO TELEGRAM ---

def resolver_chat_id(token, chat_input):
    """
    Lógica inteligente para definir o ID do Canal.
    Aceita @canal, ID numérico ou Vazio.
    """
    base_url = f"https://api.telegram.org/bot{token}"

    # CENÁRIO 1: Usuário colocou @NomeDoCanal
    if chat_input and str(chat_input).startswith("@"):
        logger.info(f"Tentando resolver o ID para o canal público: {chat_input}")
        try:
            # O método getChat funciona com @canal se o bot for admin
            response = requests.get(f"{base_url}/getChat", params={"chat_id": chat_input})
            data = response.json()

            if data.get("ok"):
                numeric_id = data["result"]["id"]
                title = data["result"].get("title", chat_input)

                print("\n" + "="*40)
                print(f"✅ CANAL PÚBLICO RECONHECIDO: {title}")
                print(f"🔁 CONVERTIDO PARA ID: {numeric_id}")
                print("="*40)
                print("⚠️  IMPORTANTE: Se você tornar o canal PRIVADO no futuro,")
                print(f"use este número ({numeric_id}) na variável CHANNEL_ID.")
                print("="*40 + "\n")
                return str(numeric_id)
            else:
                logger.error(f"Não foi possível encontrar o canal {chat_input}. O bot é admin?")
                logger.error(f"Erro Telegram: {data.get('description')}")
                # Se falhar, cai para o modo de descoberta manual
        except Exception as e:
            logger.error(f"Erro ao resolver @canal: {e}")

    # CENÁRIO 2: Usuário colocou ID Numérico direto (-100...)
    if chat_input and (str(chat_input).startswith("-100") or str(chat_input).isdigit() or str(chat_input).startswith("-")):
        logger.info(f"ID numérico detectado: {chat_input}")
        return str(chat_input)

    # CENÁRIO 3: Nada informado ou falha na resolução -> MODO DESCOBERTA
    logger.warning("CHANNEL_ID não configurado ou inválido. Iniciando modo de descoberta manual...")
    logger.warning("1. Certifique-se que o Bot é ADM do canal.")
    logger.warning("2. Envie uma mensagem no canal AGORA.")

    print("\n⏳ Aguardando interação no Telegram...\n")

    while True:
        try:
            response = requests.get(f"{base_url}/getUpdates", timeout=10)
            data = response.json()

            if data.get("ok"):
                for result in data.get("result", []):
                    # Procura por mensagens de canal
                    if 'channel_post' in result:
                        chat = result['channel_post']['chat']
                        c_id = chat['id']
                        c_title = chat['title']

                        print("\n" + "="*40)
                        print(f"✅ CANAL ENCONTRADO VIA MENSAGEM: {c_title}")
                        print(f"🆔 ID DO CANAL: {c_id}")
                        print("="*40 + "\n")
                        return str(c_id)

            time.sleep(3)
        except Exception as e:
            logger.error(f"Erro de conexão (tentando novamente): {e}")
            time.sleep(5)

def telegram_notificar_inicio(token, chat_id):
    """Envia mensagem avisando que o servidor subiu."""
    if not token or not chat_id: return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={
            "chat_id": chat_id,
            "text": "🚀 <b>Nebula FTP Online!</b>\nO servidor foi iniciado com sucesso.",
            "parse_mode": "HTML"
        })
    except Exception as e:
        logger.warning(f"Não foi possível enviar notificação de inicio: {e}")

# --- WORKER DE UPLOAD ---
async def upload_worker():
    logger.info("Worker de Upload iniciado (Aguardando arquivos...).")
    while True:
        item = await UPLOAD_QUEUE.get()
        # Placeholder para integração futura com tg.py
        # filename = item.get('filename')
        # logger.info(f"Processando upload da fila: {filename}")
        UPLOAD_QUEUE.task_done()

# --- MAIN ASSÍNCRONO ---

async def main():
    # 1. Resolver Telegram ID
    final_chat_id = None
    if TG_TOKEN:
        # Resolve o ID (converte @canal -> ID ou descobre via mensagem)
        final_chat_id = resolver_chat_id(TG_TOKEN, TG_CHAT_ID_INPUT)

        # Notifica inicio
        telegram_notificar_inicio(TG_TOKEN, final_chat_id)

        # Define no ambiente para uso global
        os.environ["CHANNEL_ID"] = str(final_chat_id)
        # Importante: O Server/PathIO podem ler de os.environ, mas também podemos injetar aqui se necessário

    # 2. Conectar ao MongoDB
    logger.info(f"Conectando ao MongoDB: {MONGODB_URI}")
    try:
        client = MongoClient(MONGODB_URI)
        db = client.ftp
        client.server_info() # Trigger conexão
        logger.info("MongoDB conectado com sucesso.")
    except Exception as e:
        logger.critical(f"Falha ao conectar no MongoDB: {e}")
        sys.exit(1)

    # 3. Inicializar FTP
    user_manager = MongoDBUserManager(db)

    # Injeção de dependência no PathIO
    MongoDBPathIO.db = db
    MongoDBPathIO.tg_token = TG_TOKEN # Se precisares passar o token pro PathIO
    MongoDBPathIO.chat_id = final_chat_id

    server = Server(user_manager, MongoDBPathIO)

    logger.info(f"Iniciando Servidor FTP em {HOST}:{PORT}")

    asyncio.create_task(upload_worker())

    try:
        await server.run(host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Servidor parando...")
        await server.close()
    except Exception as e:
        logger.critical(f"Erro fatal no servidor: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
