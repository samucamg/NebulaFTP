import asyncio
from pyrogram import Client
from itertools import cycle

class MultiBotManager:
    def __init__(self):
        self.clients = []
        self.pool = None

    async def add_bot(self, name, api_id, api_hash, bot_token):
        print(f"🤖 Iniciando {name}...")
        client = Client(name, api_id=api_id, api_hash=api_hash, bot_token=bot_token)
        await client.start()
        self.clients.append(client)
        print(f"✅ {name} Online!")

    def finalize_setup(self):
        if not self.clients:
            raise RuntimeError("Nenhum bot foi iniciado!")
        self.pool = cycle(self.clients)

    def get_next_bot(self):
        return next(self.pool)

    async def send_document(self, chat_id, document, **kwargs):
        bot = self.get_next_bot()
        return await bot.send_document(chat_id, document, **kwargs)

    # --- A MÁGICA PARA DOWNLOAD E PROXY ---
    def __getattr__(self, name):
        """Redireciona atributos desconhecidos (proxy, ipv6, etc) para o bot principal"""
        if self.clients:
            return getattr(self.clients[0], name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    async def invoke(self, *args, **kwargs):
        return await self.clients[0].invoke(*args, **kwargs)
