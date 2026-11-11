"""Painel web: login, CSRF, Origin, upload/download, Range, permissões e usuários."""
from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote

import aiohttp
import pytest

from nebula.vfs import Principal
from nebula.web.app import create_app
from tests.conftest import drain, sha

PASSWORD_SECRET = "senhaSecreta987"
DATA = os.urandom(5500)  # chunk_size do fixture é 1000: 6 partes


def _csrf_from(html: str) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m, "formulário sem campo csrf"
    return m.group(1)


class Who:
    """Cliente logado: manda o cookie de sessão explicitamente (cookie jar ignora IPs)."""

    def __init__(self, client, token: str):
        self.client = client
        self.token = token
        self.csrf = ""

    def _h(self, headers=None) -> dict:
        h = {"Cookie": f"nebula_session={self.token}"}
        h.update(headers or {})
        return h

    def get(self, url, **kw):
        headers = kw.pop("headers", None)
        return self.client.get(url, headers=self._h(headers), **kw)

    def post(self, url, **kw):
        headers = kw.pop("headers", None)
        return self.client.post(url, headers=self._h(headers), **kw)


async def login(client, who_login: str, password: str) -> Who:
    r = await client.post("/login", data={"login": who_login, "password": password}, allow_redirects=False)
    assert r.status == 302, r.status
    who = Who(client, r.cookies["nebula_session"].value)
    page = await who.get("/files")
    assert page.status == 200
    who.csrf = _csrf_from(await page.text())
    return who


async def upload(who: Who, folder: str, files: list[tuple[str, bytes]], csrf: str | None = None):
    form = aiohttp.FormData()
    form.add_field("csrf", who.csrf if csrf is None else csrf)
    form.add_field("path", folder)
    for name, data in files:
        form.add_field("files", data, filename=name, content_type="application/octet-stream")
    return await who.post("/files/upload", data=form, allow_redirects=False)


async def download_bytes(who: Who, path: str) -> tuple[int, bytes, dict]:
    r = await who.get("/files/download", params={"path": path})
    body = await r.read()
    return r.status, body, dict(r.headers)


@pytest.fixture
async def client(aiohttp_client, core):
    # DummyCookieJar: a sessão é mandada explicitamente em cada teste (um cookie por usuário).
    return await aiohttp_client(
        create_app(core.vfs, core.store, core.settings), cookie_jar=aiohttp.DummyCookieJar()
    )


@pytest.fixture
async def alice(client, core):
    return await login(client, "alice", "alicepass")


@pytest.fixture
async def admin(client, core):
    return await login(client, "admin", "adminpass")


# ---------------- login e sessão ----------------
async def test_login_ok_e_errado(client, core):
    r = await client.post("/login", data={"login": "alice", "password": "errada"}, allow_redirects=False)
    assert r.status == 401
    assert "nebula_session" not in r.cookies

    r = await client.post("/login", data={"login": "alice", "password": "alicepass"}, allow_redirects=False)
    assert r.status == 302
    assert r.headers["Location"] == "/files"
    raw = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in raw and "SameSite=Lax" in raw


async def test_sem_login_redireciona(client, core):
    for url in ("/", "/files", "/users", "/files/download?path=/x", "/files/stream?path=/x"):
        r = await client.get(url, allow_redirects=False)
        assert r.status == 302, url
        assert r.headers["Location"] == "/login", url


async def test_logout_invalida_sessao(client, core, alice):
    r = await alice.post("/logout", data={"csrf": alice.csrf}, allow_redirects=False)
    assert r.status == 302
    r = await alice.get("/files", allow_redirects=False)
    assert r.status == 302 and r.headers["Location"] == "/login"


# ---------------- CSRF e Origin ----------------
async def test_post_sem_csrf_403(client, core, alice):
    r = await alice.post("/files/mkdir", data={"path": "/", "name": "nova"}, allow_redirects=False)
    assert r.status == 403
    r = await alice.post("/files/mkdir", data={"path": "/", "name": "nova", "csrf": "errado"},
                         allow_redirects=False)
    assert r.status == 403
    assert await core.store.get_node("/alice/nova") is None


async def test_origin_externo_403(client, core, alice):
    r = await alice.post("/files/mkdir", data={"path": "/", "name": "nova", "csrf": alice.csrf},
                         headers={"Origin": "http://evil.example"}, allow_redirects=False)
    assert r.status == 403
    assert await core.store.get_node("/alice/nova") is None

    base = str(client.make_url("/")).rstrip("/")
    r = await alice.post("/files/mkdir", data={"path": "/", "name": "nova", "csrf": alice.csrf},
                         headers={"Origin": base}, allow_redirects=False)
    assert r.status == 303
    assert await core.store.get_node("/alice/nova") is not None


# ---------------- arquivos ----------------
async def test_upload_download_sha_antes_e_depois_do_worker(client, core, alice):
    r = await upload(alice, "/", [("dados.bin", DATA)])
    assert r.status == 303
    assert r.headers["Location"].startswith("/files?path=")

    status, body, _ = await download_bytes(alice, "/dados.bin")
    assert status == 200 and sha(body) == sha(DATA)

    await drain(core)
    status, body, headers = await download_bytes(alice, "/dados.bin")
    assert status == 200 and sha(body) == sha(DATA)
    assert headers["Content-Length"] == str(len(DATA))


async def test_upload_pasta_inexistente_404_e_nada_criado(client, core, alice):
    r = await upload(alice, "/nao-existe", [("x.bin", b"abc")])
    assert r.status == 404
    assert await core.store.get_node("/alice/nao-existe") is None
    assert await core.store.get_node("/alice/nao-existe/x.bin") is None
    assert await core.store.pending_count() == 0


async def test_upload_com_csrf_errado_nao_grava(client, core, alice):
    r = await upload(alice, "/", [("x.bin", b"abc")], csrf="errado")
    assert r.status == 403
    assert await core.store.get_node("/alice/x.bin") is None


async def test_alice_nao_ve_nem_baixa_arquivo_de_bob(client, core, alice, admin):
    bob = await login(client, "bob", "bobpass")
    assert (await upload(bob, "/", [("x.bin", b"segredo do bob")])).status == 303

    r = await alice.get("/files", params={"path": "/../bob"}, allow_redirects=False)
    assert r.status == 404  # vira /bob dentro da pasta da alice
    r = await alice.get("/files/download", params={"path": "/../bob/x.bin"}, allow_redirects=False)
    assert r.status == 404
    assert b"segredo do bob" not in await r.read()
    r = await alice.get("/files/download", params={"path": "/bob/x.bin"}, allow_redirects=False)
    assert r.status == 404
    r = await alice.get("/files", params={"path": "/"})
    assert "x.bin" not in await r.text()
    assert "bob" not in await r.text()


async def test_mkdir_rename_e_delete(client, core, alice):
    assert (await alice.post("/files/mkdir", data={"path": "/", "name": "pasta", "csrf": alice.csrf},
                             allow_redirects=False)).status == 303
    assert await core.store.get_node("/alice/pasta") is not None

    assert (await alice.post("/files/mkdir", data={"path": "/", "name": "pasta", "csrf": alice.csrf},
                             allow_redirects=False)).status == 409

    assert (await upload(alice, "/", [("x.bin", DATA)])).status == 303
    r = await alice.post("/files/rename", data={"path": "/x.bin", "new_name": "y.bin", "csrf": alice.csrf},
                         allow_redirects=False)
    assert r.status == 303
    status, body, _ = await download_bytes(alice, "/y.bin")
    assert status == 200 and sha(body) == sha(DATA)
    assert (await download_bytes(alice, "/x.bin"))[0] == 404

    r = await alice.post("/files/delete", data={"path": "/y.bin", "csrf": alice.csrf}, allow_redirects=False)
    assert r.status == 303
    assert (await download_bytes(alice, "/y.bin"))[0] == 404
    assert await core.store.get_node("/alice/y.bin") is None


async def test_download_nome_acentuado_usa_filename_star(client, core, alice):
    # O cliente aiohttp codifica nomes não ASCII no multipart (RFC 7578), então o arquivo entra pelo núcleo.
    w = await core.vfs.open_write(Principal("alice"), "/ação.txt")
    await w.write(b"oi")
    await w.close()
    status, body, headers = await download_bytes(alice, "/ação.txt")
    assert status == 200 and body == b"oi"
    cd = headers["Content-Disposition"]
    assert cd == "attachment; filename*=UTF-8''" + quote("ação.txt", safe="")


async def test_pagina_play_para_midia(client, core, alice):
    assert (await upload(alice, "/", [("clip.mp4", b"0" * 10)])).status == 303
    r = await alice.get("/files/play", params={"path": "/clip.mp4"})
    assert r.status == 200
    html = await r.text()
    assert "<video" in html and "/files/stream?path=%2Fclip.mp4" in html

    r = await alice.get("/files/play", params={"path": "/clip.mp4"})
    assert r.status == 200
    assert "Tocar" in await (await alice.get("/files", params={"path": "/"})).text()


# ---------------- streaming com Range ----------------
async def test_stream_sem_range_devolve_corpo_inteiro(client, core, alice):
    assert (await upload(alice, "/", [("video.mp4", DATA)])).status == 303
    await drain(core)
    r = await alice.get("/files/stream", params={"path": "/video.mp4"})
    body = await r.read()
    assert r.status == 200
    assert sha(body) == sha(DATA)
    assert r.headers["Accept-Ranges"] == "bytes"
    assert r.headers["Content-Type"] == "video/mp4"


async def _check_ranges(alice):
    n = len(DATA)

    async def get(rng):
        r = await alice.get("/files/stream", params={"path": "/video.mp4"}, headers={"Range": rng})
        return r, await r.read()

    r, body = await get("bytes=900-1100")  # cruza a fronteira entre a parte 0 e a parte 1
    assert r.status == 206
    assert body == DATA[900:1101]
    assert r.headers["Content-Range"] == f"bytes 900-1100/{n}"
    assert r.headers["Content-Length"] == "201"

    r, body = await get("bytes=-100")
    assert r.status == 206 and body == DATA[-100:]
    assert r.headers["Content-Range"] == f"bytes {n - 100}-{n - 1}/{n}"

    r, body = await get("bytes=5000-")
    assert r.status == 206 and body == DATA[5000:]
    assert r.headers["Content-Range"] == f"bytes 5000-{n - 1}/{n}"

    r, body = await get("bytes=6000-7000")
    assert r.status == 416
    assert r.headers["Content-Range"] == f"bytes */{n}"

    r, _ = await get("bytes=abc")
    assert r.status == 416


async def test_stream_range_antes_e_depois_das_partes(client, core, alice):
    assert (await upload(alice, "/", [("video.mp4", DATA)])).status == 303
    await _check_ranges(alice)  # ainda no staging local
    await drain(core)
    await _check_ranges(alice)  # agora pelas partes do cache


# ---------------- usuários ----------------
async def test_usuario_comum_nao_acessa_admin(client, core, alice):
    r = await alice.get("/users", allow_redirects=False)
    assert r.status == 403
    r = await alice.get("/users/add", allow_redirects=False)
    assert r.status == 403
    r = await alice.get("/users/edit/bob", allow_redirects=False)
    assert r.status == 403


async def test_admin_cria_usuario_e_pasta_aparece(client, core, admin):
    r = await admin.get("/users/add")
    assert r.status == 200
    form = {"login": "carol", "password": PASSWORD_SECRET, "csrf": admin.csrf}
    r = await admin.post("/users/add", data=form, allow_redirects=False)
    assert r.status == 303
    assert await core.store.get_user("carol") is not None
    assert await core.store.get_node("/carol") is not None

    root = await (await admin.get("/files", params={"path": "/"})).text()
    assert "carol/" in root


async def test_admin_recebe_erro_de_formulario_em_mensagem(client, core, admin):
    r = await admin.post("/users/add", data={"login": "alice", "password": "x", "csrf": admin.csrf},
                         allow_redirects=False)
    assert r.status == 409
    assert "Já existe um usuário" in await r.text()

    r = await admin.post("/users/add", data={"login": "a", "password": "x", "csrf": admin.csrf},
                         allow_redirects=False)
    assert r.status == 400
    assert "3 a 32" in await r.text()


async def test_admin_edita_e_remove_usuario(client, core, admin):
    await admin.post("/users/add", data={"login": "dave", "password": "x", "csrf": admin.csrf},
                     allow_redirects=False)
    r = await admin.post("/users/edit/dave", data={"password": "", "is_admin": "1", "csrf": admin.csrf},
                         allow_redirects=False)
    assert r.status == 303
    assert (await core.store.get_user("dave")).is_admin is True

    r = await admin.post("/users/delete/dave", data={"delete_files": "1", "csrf": admin.csrf},
                         allow_redirects=False)
    assert r.status == 303
    assert await core.store.get_user("dave") is None
    assert await core.store.get_node("/dave") is None


async def test_admin_principal_nao_pode_ser_removido(client, core):
    await core.vfs.add_user("boss", "bosspass", is_admin=True)
    boss = await login(client, "boss", "bosspass")
    r = await boss.post("/users/delete/admin", data={"csrf": boss.csrf}, allow_redirects=False)
    assert r.status == 403
    assert await core.store.get_user("admin") is not None

    r = await boss.post("/users/delete/boss", data={"csrf": boss.csrf}, allow_redirects=False)
    assert r.status == 400  # não apaga a própria conta
    assert await core.store.get_user("boss") is not None


async def test_senha_nao_aparece_em_paginas_nem_log(client, core, admin, caplog):
    caplog.set_level(logging.DEBUG)
    await admin.post("/users/add", data={"login": "erin", "password": PASSWORD_SECRET, "csrf": admin.csrf},
                     allow_redirects=False)
    bad = await client.post("/login", data={"login": "erin", "password": PASSWORD_SECRET + "x"},
                            allow_redirects=False)
    pages = [
        await (await admin.get("/users")).text(),
        await (await admin.get("/users/add")).text(),
        await (await admin.get("/users/edit/erin")).text(),
        await bad.text(),
        await (await client.get("/login")).text(),
    ]
    for html in pages:
        assert PASSWORD_SECRET not in html
    assert PASSWORD_SECRET not in caplog.text


async def test_html_enviado_nao_roda_no_painel(client, core, alice):
    assert (await upload(alice, "/", [("x.html", b"<script>alert(1)</script>")])).status == 303
    r = await alice.get("/files/stream", params={"path": "/x.html"})
    assert r.headers["Content-Type"].startswith("application/octet-stream")
    assert r.headers["X-Content-Type-Options"] == "nosniff"


async def test_logo_publica_sem_login_e_nada_mais(client, core):
    r = await client.get("/static/logo-mark.png", allow_redirects=False)
    assert r.status == 200 and r.content_type == "image/png"
    for bad in ("/static/../app.py", "/static/%2e%2e/app.py", "/static/..%2fapp.py"):
        r = await client.get(bad, allow_redirects=False)
        assert r.status in (302, 403, 404), bad
        assert b"aiohttp_jinja2" not in await r.read(), bad
    r = await client.get("/files", allow_redirects=False)
    assert r.status == 302
    html = await (await client.get("/login")).text()
    assert "/static/logo-full.png" in html
