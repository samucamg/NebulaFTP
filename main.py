"""NebulaFTP Community: SFTP + painel web com armazenamento no Telegram (um bot, um canal)."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

from aiohttp import web

from nebula.app import build_core
from nebula.config import Settings, setup_logging
from nebula.sftp.server import start_sftp_server
from nebula.telegram.backend import PyroBackend, clock_offset
from nebula.web.app import create_app

log = logging.getLogger("nebula")


def check_settings(s: Settings) -> list[str]:
    errs = []
    if not s.api_id or not s.api_hash:
        errs.append("API_ID e API_HASH são obrigatórios (my.telegram.org)")
    if not s.bot_token:
        errs.append("BOT_TOKENS é obrigatório (um token do @BotFather)")
    if not s.chat_id:
        errs.append("CHAT_ID é obrigatório (canal onde o bot é administrador)")
    return errs


async def run(settings: Settings) -> None:
    errs = check_settings(settings)
    if errs:
        for e in errs:
            log.error(e)
        raise SystemExit(2)

    off = await asyncio.to_thread(clock_offset)
    if off is None:
        log.warning("Não foi possível conferir o relógio (sem internet?)")
    elif abs(off) > 30:
        log.error(
            "O relógio deste computador está %.0f s diferente do horário real. "
            "O Telegram recusa a conexão com mais de 30 s de diferença. Acerte o relógio e tente de novo.", off
        )
        raise SystemExit(3)

    tg = PyroBackend(settings.api_id, settings.api_hash, settings.bot_token, settings.chat_id,
                     workdir=str(settings.data_dir))
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    core = await build_core(settings, tg)
    runner = None
    acceptor = None
    worker_task = None
    try:
        await core.vfs.ensure_admin(settings.admin_user, settings.admin_password)
        await tg.start()
        worker_task = asyncio.create_task(core.worker.run())
        acceptor = await start_sftp_server(core.vfs, settings.host, settings.sftp_port, settings.host_key)
        log.info("SFTP em %s:%s", settings.host, settings.sftp_port)
        app = create_app(core.vfs, core.store, settings)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        await web.TCPSite(runner, settings.host, settings.web_port).start()
        log.info("Painel web em http://%s:%s", settings.host, settings.web_port)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:  # Windows
                pass
        await stop.wait()
    finally:
        log.info("Encerrando...")
        core.worker.stop()
        if acceptor:
            acceptor.close()
        if runner:
            await runner.cleanup()
        if worker_task:
            try:
                await asyncio.wait_for(worker_task, 10)
            except Exception:
                pass
        await tg.stop()
        await core.store.close()


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings)
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        pass
    except SystemExit as e:
        sys.exit(e.code)


if __name__ == "__main__":
    main()
