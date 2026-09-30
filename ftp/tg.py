import logging

logger = logging.getLogger("NebulaFTP.TG")

class File:
    def __init__(self, id, client, message_id=None, chat_id=None):
        self.raw_id = id
        self.client = client
        self.message_id = message_id
        self.chat_id = chat_id

    async def stream(self, offset=0):
        try:
            chunk_offset = offset // (1024 * 1024)
            skip_bytes = offset % (1024 * 1024)
            
            target = None
            if self.message_id and self.chat_id:
                try:
                    target = await self.client.get_messages(self.chat_id, self.message_id)
                    if not target or getattr(target, 'empty', False):
                        target = None
                except Exception as e:
                    logger.warning(f"⚠️ [STREAM] Erro ao buscar mensagem {self.message_id}: {e}")
                    target = None

            if not target:
                target = self.raw_id

            async for chunk in self.client.stream_media(target, offset=chunk_offset):
                if skip_bytes > 0:
                    if len(chunk) > skip_bytes:
                        chunk = chunk[skip_bytes:]
                        skip_bytes = 0
                    else:
                        skip_bytes -= len(chunk)
                        continue
                yield chunk
        except Exception as e:
            logger.error(f"❌ [STREAM] Erro durante streaming do Telegram: {e}")
            if "MESSAGE_ID_INVALID" in str(e).upper() or "MESSAGE_DELETED" in str(e).upper():
                raise FileNotFoundError("Arquivo foi apagado no Telegram (Fantasma)") from e
            raise

async def stream_file(parts, bot, chat_id=None):
    parts.sort(key=lambda x: x["part_id"])
    for part in parts:
        file = File(part["tg_file"], bot, message_id=part.get("tg_message"), chat_id=chat_id)
        async for chunk in file.stream():
            yield chunk

