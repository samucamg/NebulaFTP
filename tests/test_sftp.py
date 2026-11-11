"""Testes do adaptador SFTP: sobe o servidor real (porta efêmera) e conecta com asyncssh."""
import hashlib
import os
import random

import asyncssh
import pytest
import pytest_asyncio

from nebula.sftp.server import _sftp_error, start_sftp_server
from nebula.vfs import Denied, Exists, Invalid, IsADir, NotADir, NotEmpty, NotFound
from tests.conftest import drain, sha

PASSWORDS = {"admin": "adminpass", "alice": "alicepass", "bob": "bobpass"}


@pytest_asyncio.fixture
async def server(core, tmp_path):
    acc = await start_sftp_server(core.vfs, "127.0.0.1", 0, tmp_path / "hostkey")
    port = acc.sockets[0].getsockname()[1]
    yield port
    acc.close()
    await acc.wait_closed()


@pytest_asyncio.fixture
async def login(server):
    """Abre conexões SFTP autenticadas. Fecha tudo no fim do teste."""
    conns = []

    async def _login(user, password=None):
        conn = await asyncssh.connect(
            "127.0.0.1", server, username=user,
            password=PASSWORDS[user] if password is None else password,
            known_hosts=None,
        )
        conns.append(conn)
        return await conn.start_sftp_client()

    yield _login
    for conn in conns:
        conn.close()
        await conn.wait_closed()


async def put(sftp, path, data):
    async with sftp.open(path, "wb") as f:
        await f.write(data)


async def get(sftp, path):
    async with sftp.open(path, "rb") as f:
        return await f.read()


# ---------------- mapeamento de erros (sem rede) ----------------
@pytest.mark.parametrize("err, sftp_cls", [
    (NotFound("/x"), asyncssh.SFTPNoSuchFile),
    (Exists("/x"), asyncssh.SFTPFileAlreadyExists),
    (Denied("/x"), asyncssh.SFTPPermissionDenied),
    (NotEmpty("/x"), asyncssh.SFTPDirNotEmpty),
    (NotADir("/x"), asyncssh.SFTPNotADirectory),
    (IsADir("/x"), asyncssh.SFTPFileIsADirectory),
    (Invalid("/x"), asyncssh.SFTPInvalidParameter),
])
def test_mapeamento_de_erros_do_nucleo(err, sftp_cls):
    assert isinstance(_sftp_error(err), sftp_cls)


# ---------------- raiz e isolamento ----------------
async def test_realpath_do_usuario_e_raiz(login):
    alice = await login("alice")
    assert await alice.realpath(".") == "/"


async def test_listdir_mostra_so_a_propria_pasta(login):
    alice = await login("alice")
    bob = await login("bob")
    await put(bob, "/segredo_bob.txt", b"bob")
    await put(alice, "/nota.txt", b"alice")

    names = {n for n in await alice.listdir("/") if n not in (".", "..")}
    assert "nota.txt" in names
    assert "bob" not in names
    assert "admin" not in names
    assert "segredo_bob.txt" not in names


async def test_alice_nao_alcanca_outros_usuarios(login):
    alice = await login("alice")
    bob = await login("bob")
    await put(bob, "/segredo_bob.txt", b"bob")

    # ".." na raiz fica na raiz: "/../bob" vira "/bob" dentro da pasta da alice
    with pytest.raises(asyncssh.SFTPNoSuchFile):
        await alice.stat("/../bob")
    with pytest.raises(asyncssh.SFTPNoSuchFile):
        await alice.open("/../bob/segredo_bob.txt", "rb")
    assert await alice.realpath("/../..") == "/"
    # "/bob" existe só na visão do admin; para alice é um caminho inexistente
    with pytest.raises(asyncssh.SFTPNoSuchFile):
        await alice.stat("/bob")
    with pytest.raises(asyncssh.SFTPNoSuchFile):
        await alice.stat("/bob/segredo_bob.txt")


async def test_caminho_invalido_e_rejeitado(login):
    alice = await login("alice")
    with pytest.raises(asyncssh.SFTPError):
        await alice.stat(b"/\x81\x8d")  # nem UTF-8 nem cp1252


async def test_nome_em_cp1252_funciona(login):
    alice = await login("alice")
    async with alice.open(b"/Epis\xf3dio 1!.mp4", "wb") as f:  # cliente Windows em cp1252
        await f.write(b"video")
    assert (await alice.stat("/Episódio 1!.mp4")).size == 5


async def test_admin_ve_todos_os_usuarios(login):
    admin = await login("admin")
    names = set(await admin.listdir("/"))
    assert {"alice", "bob"} <= names


# ---------------- integridade e partes ----------------
async def test_upload_download_sha_antes_e_depois_do_worker(login, core):
    alice = await login("alice")
    data = os.urandom(5500)
    await put(alice, "/grande.bin", data)

    # antes do worker: lê do staging local
    assert sha(await get(alice, "/grande.bin")) == sha(data)

    await drain(core)

    # depois do worker: lê das partes de 1000 bytes no FakeTelegram
    back = await get(alice, "/grande.bin")
    assert len(back) == 5500
    assert hashlib.sha256(back).hexdigest() == hashlib.sha256(data).hexdigest()
    assert core.tg.uploads == 6  # 5500 bytes / 1000 por parte


async def test_leitura_em_offsets_aleatorios_de_varias_partes(login, core):
    alice = await login("alice")
    data = os.urandom(5500)
    await put(alice, "/partes.bin", data)
    await drain(core)

    rnd = random.Random(42)
    casos = [(0, 1), (999, 2), (1000, 1), (4999, 501), (5499, 1)]
    casos += [(rnd.randrange(0, 5500), rnd.randrange(1, 1500)) for _ in range(20)]
    async with alice.open("/partes.bin", "rb") as f:
        for off, size in casos:
            got = await f.read(size, off)
            assert got == data[off:off + size], (off, size)


async def test_arquivo_vazio_existe_com_tamanho_zero(login, core):
    alice = await login("alice")
    async with alice.open("/vazio.txt", "wb"):
        pass
    assert await alice.exists("/vazio.txt")
    assert (await alice.stat("/vazio.txt")).size == 0
    await drain(core)
    assert (await alice.stat("/vazio.txt")).size == 0
    assert await get(alice, "/vazio.txt") == b""


async def test_sobrescrita_troca_o_conteudo(login, core):
    alice = await login("alice")
    await put(alice, "/x.txt", b"A" * 2500)
    await drain(core)
    await put(alice, "/x.txt", b"novo")
    await drain(core)
    assert await get(alice, "/x.txt") == b"novo"


async def test_append_preserva_conteudo_depois_do_worker(login, core):
    alice = await login("alice")
    await put(alice, "/log.txt", b"HELLO ")
    await drain(core)
    async with alice.open("/log.txt", "ab") as f:
        await f.write(b"WORLD")
    await drain(core)
    assert await get(alice, "/log.txt") == b"HELLO WORLD"


# ---------------- atributos ----------------
async def test_utime_e_setstat_nao_falham_e_mudam_mtime(login):
    alice = await login("alice")
    await put(alice, "/t.txt", b"abc")

    await alice.utime("/t.txt", (1_500_000_000.0, 1_500_000_000.0))
    assert abs((await alice.stat("/t.txt")).mtime - 1_500_000_000) < 2

    # SFTPv3 só transporta atime e mtime juntos (flag ACMODTIME)
    await alice.setstat("/t.txt", asyncssh.SFTPAttrs(atime=1_600_000_000, mtime=1_600_000_000))
    assert abs((await alice.stat("/t.txt")).mtime - 1_600_000_000) < 2

    await alice.chmod("/t.txt", 0o600)  # permissões são ignoradas, sem erro
    assert await get(alice, "/t.txt") == b"abc"


# ---------------- nomes e pastas ----------------
async def test_rename_e_posix_rename(login):
    alice = await login("alice")
    await put(alice, "/a.txt", b"conteudo-a")
    await alice.rename("/a.txt", "/b.txt")
    assert not await alice.exists("/a.txt")
    assert await get(alice, "/b.txt") == b"conteudo-a"

    await put(alice, "/c.txt", b"conteudo-c")
    # SFTPv3 rebaixa códigos novos para FX_FAILURE; o mapeamento fino é testado em _sftp_error
    with pytest.raises(asyncssh.SFTPError):
        await alice.rename("/b.txt", "/c.txt")
    assert await get(alice, "/c.txt") == b"conteudo-c"

    await alice.posix_rename("/b.txt", "/c.txt")
    assert not await alice.exists("/b.txt")
    assert await get(alice, "/c.txt") == b"conteudo-a"


async def test_mkdir_rmdir(login):
    alice = await login("alice")
    await alice.mkdir("/pasta")
    assert await alice.isdir("/pasta")
    with pytest.raises(asyncssh.SFTPError):
        await alice.mkdir("/pasta")

    await put(alice, "/pasta/x.txt", b"x")
    with pytest.raises(asyncssh.SFTPError):
        await alice.rmdir("/pasta")

    await alice.remove("/pasta/x.txt")
    await alice.rmdir("/pasta")
    assert not await alice.exists("/pasta")


async def test_remove_arquivo_e_recusa_pasta(login):
    alice = await login("alice")
    await put(alice, "/r.txt", b"r")
    await alice.remove("/r.txt")
    assert not await alice.exists("/r.txt")

    await alice.mkdir("/d")
    with pytest.raises(asyncssh.SFTPError):
        await alice.remove("/d")
    assert await alice.isdir("/d")


async def test_symlink_e_readlink_nao_suportados(login):
    alice = await login("alice")
    await put(alice, "/alvo.txt", b"alvo")
    with pytest.raises(asyncssh.SFTPOpUnsupported):
        await alice.symlink("/alvo.txt", "/link")
    with pytest.raises(asyncssh.SFTPOpUnsupported):
        await alice.readlink("/alvo.txt")


# ---------------- sessão ----------------
async def test_senha_errada_falha(server):
    with pytest.raises(asyncssh.PermissionDenied):
        await asyncssh.connect(
            "127.0.0.1", server, username="alice", password="errada", known_hosts=None
        )


async def test_shell_e_exec_desabilitados(server):
    conn = await asyncssh.connect(
        "127.0.0.1", server, username="alice", password="alicepass", known_hosts=None
    )
    try:
        with pytest.raises(asyncssh.Error):
            await conn.run("echo oi", check=True)
    finally:
        conn.close()
        await conn.wait_closed()


async def test_sentinela_fora_do_sistema_nao_muda(login, core, tmp_path):
    sentinela = tmp_path / "sentinela.txt"
    sentinela.write_bytes(b"nao mexer")
    antes = hashlib.sha256(sentinela.read_bytes()).hexdigest()

    alice = await login("alice")
    await put(alice, "/s.txt", b"dados")
    await alice.rename("/s.txt", "/s2.txt")
    await alice.remove("/s2.txt")
    await drain(core)

    assert hashlib.sha256(sentinela.read_bytes()).hexdigest() == antes


async def test_statvfs_e_realpath_vazio(login):
    alice = await login("alice")
    v = await alice.statvfs("/")
    assert v.bsize == 4096 and v.bavail > 0
    assert await alice.realpath("") == "/"
    assert await alice.realpath(".") == "/"
