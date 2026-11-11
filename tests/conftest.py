import hashlib

import pytest
import pytest_asyncio

from nebula.app import build_core
from nebula.config import Settings
from nebula.telegram.fake import FakeTelegram


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_file=tmp_path / "t.db",
        data_dir=tmp_path / "data",
        admin_user="admin",
        admin_password="adminpass",
        chunk_size=1000,  # partes pequenas para testar várias partes
        host="127.0.0.1",
        host_key=tmp_path / "hostkey",
    )


@pytest_asyncio.fixture
async def core(settings):
    tg = FakeTelegram()
    c = await build_core(settings, tg)
    await c.vfs.ensure_admin("admin", "adminpass")
    await c.vfs.add_user("alice", "alicepass")
    await c.vfs.add_user("bob", "bobpass")
    yield c
    await c.store.close()


async def drain(core):
    """Roda o worker até não haver mais nada pendente."""
    for _ in range(200):
        await core.store.db.execute("UPDATE versions SET next_try=0")  # ignora o backoff no teste
        await core.store.db.commit()
        await core.worker.step()
        if not await core.store.pending_count() and not await core.store.trash_batch():
            return
    raise AssertionError("worker não esvaziou a fila")
