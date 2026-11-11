import os

import pytest

from nebula import security
from nebula.blobs import Blobs
from nebula.store import Store
from nebula.telegram.worker import UploadWorker
from nebula.vfs import Denied, Exists, Invalid, IsADir, NebulaVFS, NotEmpty, NotFound, Principal
from tests.conftest import drain, sha

A = Principal("alice")
B = Principal("bob")
ADM = Principal("admin", True)


async def put(vfs, p, path, data, **kw):
    h = await vfs.open_write(p, path, **kw)
    if data:
        await h.write(data, 0)
    await h.close()


async def get(vfs, p, path):
    h = await vfs.open_read(p, path)
    try:
        return await h.read(0, h.size + 10)
    finally:
        await h.close()


# ---------- segurança ----------
@pytest.mark.parametrize("bad", ["", ".", "..", "a/b", "a\\b", "ab", "x" * 33, "é_acento"])
async def test_login_invalido(core, bad):
    with pytest.raises(Invalid):
        await core.vfs.add_user(bad, "senha")


async def test_senha_com_hash(core):
    u = await core.store.get_user("alice")
    assert "alicepass" not in u.password_hash and u.password_hash.startswith("scrypt$")
    assert await core.vfs.authenticate("alice", "alicepass") == A
    assert await core.vfs.authenticate("alice", "errada") is None
    assert await core.vfs.authenticate("ninguem", "x") is None


async def test_chroot_e_isolamento(core):
    await put(core.vfs, B, "/segredo.txt", b"bob")
    assert core.vfs.real(A, "/") == "/alice"
    assert [s.name for s in await core.vfs.listdir(A, "/")] == []
    for path in ("/../bob/segredo.txt", "/..", "../../bob", "/../../bob/segredo.txt"):
        assert core.vfs.real(A, path).startswith("/alice")
        with pytest.raises((Denied, NotFound, IsADir)):
            await core.vfs.open_read(A, path)
    with pytest.raises(NotFound):
        await core.vfs.open_read(A, "/bob/segredo.txt")  # vira /alice/bob/segredo.txt
    names = {s.name for s in await core.vfs.listdir(ADM, "/")}
    assert {"alice", "bob", "admin"} <= names
    st = await core.vfs.stat(B, "/segredo.txt")
    with pytest.raises(Denied):
        await core.vfs.stat_by_id(A, st.node_id)


async def test_usuario_nao_remove_nem_renomeia_raiz(core):
    with pytest.raises(Denied):
        await core.vfs.delete(A, "/")
    with pytest.raises(Denied):
        await core.vfs.rename(A, "/", "/x")


# ---------- dados ----------
async def test_ida_e_volta_varias_partes(core):
    data = os.urandom(5500)
    await put(core.vfs, A, "/a.bin", data)
    assert await get(core.vfs, A, "/a.bin") == data  # ainda no staging
    await drain(core)
    assert core.tg.uploads == 6
    st = await core.vfs.stat(A, "/a.bin")
    assert st.size == 5500 and st.synced
    assert not list(core.blobs.staging_dir.glob("*.tmp"))
    assert sha(await get(core.vfs, A, "/a.bin")) == sha(data)
    h = await core.vfs.open_read(A, "/a.bin")
    assert await h.read(990, 30) == data[990:1020]  # cruza fronteira de parte
    assert await h.read(5490, 100) == data[5490:]
    await h.close()


async def test_append_preserva_conteudo(core):
    await put(core.vfs, A, "/h.txt", b"HELLO ")
    await drain(core)
    await put(core.vfs, A, "/h.txt", b"WORLD", truncate=False, append=True)
    got = await get(core.vfs, A, "/h.txt")
    assert got == b"HELLO WORLD"
    assert sha(got) == "787ec76dcafd20c1908eb0936a12f91edd105ab5cd7ecc2b1ae2032648345dff"
    await drain(core)
    assert await get(core.vfs, A, "/h.txt") == b"HELLO WORLD"


async def test_escrita_parcial_com_offset(core):
    await put(core.vfs, A, "/p.bin", b"0123456789")
    await drain(core)
    h = await core.vfs.open_write(A, "/p.bin", truncate=False)
    await h.write(b"ab", 3)
    await h.close()
    assert await get(core.vfs, A, "/p.bin") == b"012ab56789"


async def test_arquivo_vazio_existe_e_nao_vai_ao_telegram(core):
    h = await core.vfs.open_write(A, "/vazio.txt")
    st = await core.vfs.stat(A, "/vazio.txt")  # existe antes do close
    assert st.size == 0
    await h.close()
    await drain(core)
    assert (await core.vfs.stat(A, "/vazio.txt")).size == 0
    assert core.tg.uploads == 0
    assert await get(core.vfs, A, "/vazio.txt") == b""


async def test_sobrescrever_apaga_partes_antigas(core):
    await put(core.vfs, A, "/o.bin", os.urandom(2500))
    await drain(core)
    old = set(core.tg.docs)
    await put(core.vfs, A, "/o.bin", b"novo")
    await drain(core)
    assert old <= set(core.tg.deleted)
    assert await get(core.vfs, A, "/o.bin") == b"novo"


async def test_apagar_pasta_recursiva_apaga_partes(core):
    await core.vfs.mkdir(A, "/d")
    await core.vfs.mkdir(A, "/d/e")
    await put(core.vfs, A, "/d/e/f.bin", os.urandom(1500))
    await put(core.vfs, A, "/d/g.bin", os.urandom(800))
    await drain(core)
    sent = set(core.tg.docs)
    await core.vfs.delete(A, "/d")
    await drain(core)
    assert sent <= set(core.tg.deleted)
    assert await core.vfs.listdir(A, "/") == []


async def test_renomear_pasta_move_filhos(core):
    await core.vfs.mkdir(A, "/p1")
    await core.vfs.mkdir(A, "/p1/a")
    data = os.urandom(1200)
    await put(core.vfs, A, "/p1/a/b.txt", data)
    await drain(core)
    await core.vfs.rename(A, "/p1", "/p2")
    assert await get(core.vfs, A, "/p2/a/b.txt") == data
    with pytest.raises(NotFound):
        await core.vfs.stat(A, "/p1/a/b.txt")
    assert [s.name for s in await core.vfs.listdir(A, "/p2/a")] == ["b.txt"]


async def test_rename_regras(core):
    await put(core.vfs, A, "/x", b"x")
    await put(core.vfs, A, "/y", b"y")
    with pytest.raises(Exists):
        await core.vfs.rename(A, "/x", "/y")
    await core.vfs.rename(A, "/x", "/y", overwrite=True)
    assert await get(core.vfs, A, "/y") == b"x"
    await core.vfs.mkdir(A, "/dd")
    with pytest.raises(Invalid):
        await core.vfs.rename(A, "/dd", "/dd/sub")


async def test_mkdir_regras(core):
    await put(core.vfs, A, "/arq", b"1")
    with pytest.raises(Exists):
        await core.vfs.mkdir(A, "/arq")
    with pytest.raises(Exists):
        await core.vfs.mkdir(A, "/arq", exist_ok=True)
    await core.vfs.mkdir(A, "/dir")
    await core.vfs.mkdir(A, "/dir", exist_ok=True)
    with pytest.raises(Exists):
        await core.vfs.mkdir(A, "/dir")
    with pytest.raises(NotFound):
        await core.vfs.mkdir(A, "/nao/existe")
    with pytest.raises(NotFound):
        await put(core.vfs, A, "/nao/existe.txt", b"x")
    await core.vfs.mkdir(A, "/dir/sub")
    with pytest.raises(NotEmpty):
        await core.vfs.rmdir(A, "/dir")
    with pytest.raises(IsADir):
        await core.vfs.open_write(A, "/dir")


async def test_falha_de_envio_reagenda_sem_perder(core):
    core.tg.fail_uploads = 2
    data = os.urandom(300)
    await put(core.vfs, A, "/f.bin", data)
    await core.worker.step()
    v = await core.store.next_pending(10**12)
    assert v and v.attempts == 1
    await core.store.db.execute("UPDATE versions SET next_try=0")
    await core.store.db.commit()
    await drain(core)
    assert await get(core.vfs, A, "/f.bin") == data
    assert await core.store.pending_count() == 0


async def test_reinicio_retoma_envio_pendente(settings):
    from nebula.app import build_core
    from nebula.telegram.fake import FakeTelegram

    tg = FakeTelegram()
    c1 = await build_core(settings, tg)
    await c1.vfs.add_user("alice", "alicepass")
    data = os.urandom(2100)
    await put(c1.vfs, A, "/r.bin", data)
    await c1.store.close()  # "queda" antes do worker enviar

    c2 = await build_core(settings, tg)
    assert await c2.store.pending_count() == 1
    await drain(c2)
    assert await get(c2.vfs, A, "/r.bin") == data
    await c2.store.close()


async def test_versao_substituida_durante_envio_e_descartada(core):
    await put(core.vfs, A, "/s.bin", os.urandom(2500))
    v = await core.store.next_pending(10**12)
    await put(core.vfs, A, "/s.bin", b"final")  # substitui antes do envio
    await core.worker.upload_version(v)
    await drain(core)
    assert await get(core.vfs, A, "/s.bin") == b"final"
    assert list(core.tg.docs.values()) == [b"final"]  # nada do arquivo velho ficou no canal


async def test_gc_nao_apaga_cache_em_uso(core):
    data = os.urandom(2500)
    await put(core.vfs, A, "/c.bin", data)
    await drain(core)
    h = await core.vfs.open_read(A, "/c.bin")
    assert await h.read(0, 10) == data[:10]
    removed = await core.blobs.gc(max_cache_age=-1, max_staging_age=-1)
    assert await h.read(10, 2000) == data[10:2010]
    await h.close()
    assert removed >= 0


async def test_gc_nao_apaga_staging_referenciado(core):
    data = os.urandom(500)
    await put(core.vfs, A, "/st.bin", data)
    await core.blobs.gc(max_cache_age=-1, max_staging_age=-1)
    await drain(core)
    assert await get(core.vfs, A, "/st.bin") == data


async def test_normalize():
    assert security.normalize("/a/./b//c/") == "/a/b/c"
    assert security.normalize("a\\b") == "/a/b"
    assert security.normalize("/../x") == "/x"
    assert security.normalize("/a/../../..") == "/"


async def test_leituras_concorrentes_no_mesmo_handle(core):
    import asyncio
    data = os.urandom(5000)
    await put(core.vfs, A, "/cc.bin", data)
    await drain(core)
    h = await core.vfs.open_read(A, "/cc.bin")
    offs = [4100, 100, 3050, 1990, 0, 4999, 2500]
    got = await asyncio.gather(*(h.read(o, 64) for o in offs))
    await h.close()
    assert all(g == data[o:o + 64] for g, o in zip(got, offs))


async def test_recriar_login_nao_herda_arquivos(core):
    await put(core.vfs, B, "/antigo.txt", b"x")
    await core.vfs.delete_user("bob")
    await core.vfs.add_user("bob", "nova")
    assert await core.vfs.listdir(B, "/") == []
    names = {s.name for s in await core.vfs.listdir(ADM, "/")}
    assert any(n.startswith("bob.removido-") for n in names)


async def test_usuario_duplicado(core):
    with pytest.raises(Exists):
        await core.vfs.add_user("alice", "x")


async def test_leitura_em_handle_de_escrita(core):
    await put(core.vfs, A, "/rw.bin", b"0123456789")
    await drain(core)
    h = await core.vfs.open_write(A, "/rw.bin", truncate=False)
    assert await h.read(2, 3) == b"234"
    await h.write(b"XY", 0)
    assert await h.read(0, 4) == b"XY23"
    await h.close()
    assert await get(core.vfs, A, "/rw.bin") == b"XY23456789"


async def test_bloqueio_apos_5_senhas_erradas(core):
    for _ in range(5):
        assert await core.vfs.authenticate("alice", "errada") is None
    assert await core.vfs.authenticate("alice", "alicepass") is None  # bloqueado
    core.vfs._fails.clear()
    assert await core.vfs.authenticate("alice", "alicepass") == A
