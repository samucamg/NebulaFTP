"""Painel web do NebulaFTP Community.

Adaptador fino: só chama o núcleo (NebulaVFS e Store). Nenhum SQL e nenhuma lógica de arquivo aqui.
"""
from __future__ import annotations

import hmac
import logging
import mimetypes
import os
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlencode, urlsplit

import aiohttp_jinja2
import jinja2
from aiohttp import web

from .. import security
from ..config import Settings
from ..security import PathError
from ..store import Store
from ..vfs import (
    Denied, Exists, FSError, Invalid, IsADir, NebulaVFS, NotADir, NotEmpty, NotFound, Principal,
)

COOKIE = "nebula_session"
SESSION_TTL = 12 * 3600
CHUNK = 1024 * 1024
TEMPLATES = Path(__file__).parent / "templates"
MEDIA = {
    ".mp4": "video", ".webm": "video",
    ".mp3": "audio", ".m4a": "audio", ".ogg": "audio", ".opus": "audio", ".wav": "audio",
}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_PATHS = {"/login"}
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")

# Tipos que o mimetypes do Python pode não conhecer em todas as plataformas.
mimetypes.add_type("audio/ogg", ".opus")
mimetypes.add_type("audio/mp4", ".m4a")

log = logging.getLogger("nebula.web")

VFS = web.AppKey("vfs", NebulaVFS)
STORE = web.AppKey("store", Store)
SETTINGS = web.AppKey("settings", Settings)
PRINCIPAL = web.RequestKey("principal", Principal)
CSRF = web.RequestKey("csrf", str)
SESSION = web.RequestKey("session", str)


# ---------------- utilitários ----------------
def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _vpath(raw: Optional[str]) -> str:
    """Caminho virtual normalizado. Tentativa de subir acima da raiz vira 403."""
    try:
        return security.normalize(raw or "/")
    except PathError as e:
        raise Denied(str(e)) from e


def _back(path: str) -> str:
    return "/files?" + urlencode({"path": path})


def _parent(path: str) -> str:
    return security.split(path)[0]


def _safe_filename(raw: str) -> str:
    base = unicodedata.normalize("NFC", (raw or "").replace("\\", "/").rsplit("/", 1)[-1]).strip()
    if not security.valid_name(base):
        raise Invalid("nome de arquivo inválido")
    return base


def _check_csrf(request: web.Request, token) -> None:
    expected = request.get(CSRF)
    sent = _text(token)
    if not expected or not sent or not hmac.compare_digest(sent, expected):
        raise web.HTTPForbidden(text="Falha na verificação CSRF. Recarregue a página e tente de novo.")


def _ctx(request: web.Request, **extra) -> dict:
    return {
        "request": request,
        "me": request.get(PRINCIPAL),
        "csrf": request.get(CSRF) or "",
        **extra,
    }


def _require_admin(request: web.Request) -> Principal:
    p: Principal = request[PRINCIPAL]
    if not p.is_admin:
        raise Denied("apenas o admin")
    return p


def _filesize(n) -> str:
    size = float(n or 0)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def _dt(ts) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def _crumbs(path: str) -> list[dict]:
    out = [{"name": "Início", "path": "/"}]
    acc = ""
    for part in [c for c in path.split("/") if c]:
        acc += "/" + part
        out.append({"name": part, "path": acc})
    return out


def _content_disposition(name: str) -> str:
    return "attachment; filename*=UTF-8''" + quote(name, safe="")


def _parse_range(header: str, size: int) -> tuple[int, int]:
    """Converte 'bytes=a-b', 'bytes=a-' e 'bytes=-n' em (início, fim) inclusivos. ValueError se inválido."""
    m = _RANGE_RE.match(header.strip())
    if not m or (m.group(1) == "" and m.group(2) == ""):
        raise ValueError(header)
    a, b = m.group(1), m.group(2)
    if a == "":  # sufixo: últimos n bytes
        n = int(b)
        if n == 0 or size == 0:
            raise ValueError(header)
        return max(0, size - n), size - 1
    start = int(a)
    end = size - 1 if b == "" else min(int(b), size - 1)
    if start > end or start >= size:
        raise ValueError(header)
    return start, end


async def _send_range(rh, resp: web.StreamResponse, offset: int, remaining: int) -> None:
    while remaining > 0:
        block = await rh.read(offset, min(CHUNK, remaining))
        if not block:
            raise IOError("conteúdo do arquivo mais curto que o anunciado")
        await resp.write(block)
        offset += len(block)
        remaining -= len(block)


# ---------------- erros ----------------
_ERROR_TEXT = {
    NotFound: "Item não encontrado.",
    Denied: "Acesso negado.",
    Exists: "Já existe um item com esse nome.",
    IsADir: "Esse caminho é uma pasta.",
    NotADir: "Esse caminho não é uma pasta.",
    NotEmpty: "A pasta não está vazia.",
    PathError: "Caminho inválido.",
}
_ERROR_STATUS = {
    NotFound: 404, Denied: 403, Exists: 409, IsADir: 409, NotADir: 409, NotEmpty: 409,
    Invalid: 400, PathError: 400,
}


def _error_response(request: web.Request, exc: Exception) -> web.Response:
    status, msg = 400, "Requisição inválida."
    for cls, code in _ERROR_STATUS.items():
        if isinstance(exc, cls):
            status = code
            msg = str(exc) if cls is Invalid else _ERROR_TEXT.get(cls, msg)
            break
    return aiohttp_jinja2.render_template(
        "error.html", request, _ctx(request, status=status, message=msg), status=status
    )


@web.middleware
async def _middleware(request: web.Request, handler):
    if request.method not in SAFE_METHODS:
        origin = request.headers.get("Origin")
        if origin is not None and urlsplit(origin).netloc.lower() != request.host.lower():
            raise web.HTTPForbidden(text="Origem não permitida.")

    store = request.app[STORE]
    principal = None
    csrf = None
    token = request.cookies.get(COOKIE)
    if token:
        sess = await store.get_session(token)
        if sess:
            user = await store.get_user(sess[0])
            if user:
                principal = Principal(user.login, user.is_admin)
                csrf = sess[1]
    request[PRINCIPAL] = principal
    request[CSRF] = csrf
    request[SESSION] = token if principal else None

    if principal is None and request.path not in PUBLIC_PATHS:
        raise web.HTTPFound("/login")

    try:
        return await handler(request)
    except (FSError, PathError) as e:
        return _error_response(request, e)


# ---------------- sessão ----------------
async def login_get(request: web.Request):
    return aiohttp_jinja2.render_template("login.html", request, _ctx(request, error=None, login=""))


async def login_post(request: web.Request):
    form = await request.post()
    login = _text(form.get("login")).strip()
    password = _text(form.get("password"))
    store = request.app[STORE]
    p = await request.app[VFS].authenticate(login, password, ip=request.remote or "")
    if p is None:
        log.info("login recusado para %r", login)
        return aiohttp_jinja2.render_template(
            "login.html", request, _ctx(request, error="Usuário ou senha inválidos.", login=login), status=401
        )
    old = request.cookies.get(COOKIE)
    if old:
        await store.delete_session(old)
    token = security.new_token()
    csrf = security.new_token()
    await store.add_session(token, p.login, csrf, time.time() + SESSION_TTL)
    resp = web.HTTPFound("/files")
    resp.set_cookie(
        COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="Lax", secure=request.secure, path="/"
    )
    raise resp


async def logout_post(request: web.Request):
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    if request[SESSION]:
        await request.app[STORE].delete_session(request[SESSION])
    resp = web.HTTPFound("/login")
    resp.del_cookie(COOKIE, path="/")
    raise resp


async def index(request: web.Request):
    raise web.HTTPFound("/files")


# ---------------- arquivos ----------------
async def files_get(request: web.Request):
    vfs = request.app[VFS]
    p = request[PRINCIPAL]
    path = _vpath(request.query.get("path", "/"))
    children = await vfs.listdir(p, path)
    items = []
    for st in children:
        ext = os.path.splitext(st.name)[1].lower()
        items.append({
            "name": st.name,
            "path": st.path,
            "is_dir": st.is_dir,
            "size": st.size,
            "mtime": st.mtime,
            "synced": st.synced,
            "media": None if st.is_dir else MEDIA.get(ext),
        })
    return aiohttp_jinja2.render_template(
        "files.html", request,
        _ctx(request, path=path, crumbs=_crumbs(path), items=items, is_admin=p.is_admin),
    )


async def mkdir_post(request: web.Request):
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    path = _vpath(_text(form.get("path")) or "/")
    name = _text(form.get("name")).strip()
    if not security.valid_name(name):
        raise Invalid("nome de pasta inválido")
    await request.app[VFS].mkdir(request[PRINCIPAL], security.join(path, name))
    raise web.HTTPSeeOther(_back(path))


async def upload_post(request: web.Request):
    vfs = request.app[VFS]
    p = request[PRINCIPAL]
    reader = await request.multipart()
    csrf_seen = False
    folder: Optional[str] = None
    while True:
        part = await reader.next()
        if part is None:
            break
        field = part.name or ""
        if field == "csrf":
            _check_csrf(request, await part.text())
            csrf_seen = True
        elif field == "path":
            if not csrf_seen:
                raise web.HTTPForbidden(text="Falha na verificação CSRF.")
            folder = _vpath(await part.text())
            st = await vfs.stat(p, folder)  # 404 antes de gravar qualquer coisa
            if not st.is_dir:
                raise NotADir(folder)
        elif field == "files" and part.filename:
            if not csrf_seen:
                raise web.HTTPForbidden(text="Falha na verificação CSRF.")
            if folder is None:
                raise Invalid("pasta de destino não informada")
            dest = security.join(folder, _safe_filename(part.filename))
            wh = await vfs.open_write(p, dest)
            try:
                while True:
                    chunk = await part.read_chunk(CHUNK)
                    if not chunk:
                        break
                    await wh.write(chunk)
                await wh.close()
            except BaseException:
                await wh.abort()
                raise
    if not csrf_seen:
        raise web.HTTPForbidden(text="Falha na verificação CSRF.")
    if folder is None:
        raise Invalid("pasta de destino não informada")
    raise web.HTTPSeeOther(_back(folder))


async def rename_post(request: web.Request):
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    src = _vpath(_text(form.get("path")))
    new_name = _text(form.get("new_name")).strip()
    if not security.valid_name(new_name):
        raise Invalid("novo nome inválido")
    parent = _parent(src)
    await request.app[VFS].rename(request[PRINCIPAL], src, security.join(parent, new_name))
    raise web.HTTPSeeOther(_back(parent))


async def delete_post(request: web.Request):
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    src = _vpath(_text(form.get("path")))
    parent = _parent(src)
    await request.app[VFS].delete(request[PRINCIPAL], src)
    raise web.HTTPSeeOther(_back(parent))


async def download_get(request: web.Request):
    vfs = request.app[VFS]
    p = request[PRINCIPAL]
    if "path" not in request.query:
        raise Invalid("caminho não informado")
    path = _vpath(request.query["path"])
    name = security.split(path)[1] or "download"
    rh = await vfs.open_read(p, path)
    try:
        resp = web.StreamResponse(status=200, headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": str(rh.size),
            "Content-Disposition": _content_disposition(name),
        })
        await resp.prepare(request)
        await _send_range(rh, resp, 0, rh.size)
        await resp.write_eof()
        return resp
    finally:
        await rh.close()


async def stream_get(request: web.Request):
    vfs = request.app[VFS]
    p = request[PRINCIPAL]
    if "path" not in request.query:
        raise Invalid("caminho não informado")
    path = _vpath(request.query["path"])
    name = security.split(path)[1] or "arquivo"
    rh = await vfs.open_read(p, path)
    try:
        size = rh.size
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        if not (ctype.startswith("video/") or ctype.startswith("audio/")):
            ctype = "application/octet-stream"  # HTML/SVG enviado por usuário nunca roda no painel
        headers = {
            "Accept-Ranges": "bytes", "Content-Type": ctype,
            "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox",
        }
        header = request.headers.get("Range")
        if header is None:
            start, end, status = 0, size - 1, 200
        else:
            try:
                start, end = _parse_range(header, size)
            except ValueError:
                return web.Response(status=416, headers={
                    "Accept-Ranges": "bytes", "Content-Range": f"bytes */{size}",
                })
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        length = max(0, end - start + 1)
        headers["Content-Length"] = str(length)
        resp = web.StreamResponse(status=status, headers=headers)
        await resp.prepare(request)
        await _send_range(rh, resp, start, length)
        await resp.write_eof()
        return resp
    finally:
        await rh.close()


async def play_get(request: web.Request):
    vfs = request.app[VFS]
    p = request[PRINCIPAL]
    path = _vpath(request.query.get("path"))
    st = await vfs.stat(p, path)
    if st.is_dir:
        raise Invalid("essa é uma pasta")
    kind = MEDIA.get(os.path.splitext(st.name)[1].lower())
    if kind is None:
        raise Invalid("formato não suportado para reproduzir no navegador")
    src = "/files/stream?" + urlencode({"path": path})
    dl = "/files/download?" + urlencode({"path": path})
    return aiohttp_jinja2.render_template(
        "play.html", request,
        _ctx(request, name=st.name, kind=kind, src=src, download=dl, back=_back(_parent(path))),
    )


# ---------------- usuários (só admin) ----------------
async def _render_users(request: web.Request, error: Optional[str] = None, status: int = 200):
    users = await request.app[STORE].list_users()
    return aiohttp_jinja2.render_template(
        "users.html", request,
        _ctx(request, users=users, admin_login=request.app[VFS].admin_login, error=error),
        status=status,
    )


async def users_get(request: web.Request):
    _require_admin(request)
    return await _render_users(request)


def _user_form(request: web.Request, *, mode: str, login: str = "", is_admin: bool = False,
               error: Optional[str] = None, status: int = 200):
    locked = mode == "edit" and login == request.app[VFS].admin_login
    return aiohttp_jinja2.render_template(
        "user_form.html", request,
        _ctx(request, mode=mode, login=login, is_admin=is_admin, error=error, locked=locked),
        status=status,
    )


async def users_add_get(request: web.Request):
    _require_admin(request)
    return _user_form(request, mode="add")


async def users_add_post(request: web.Request):
    _require_admin(request)
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    login = _text(form.get("login")).strip()
    password = _text(form.get("password"))
    is_admin = "is_admin" in form
    try:
        await request.app[VFS].add_user(login, password, is_admin)
    except Exists:
        return _user_form(request, mode="add", login=login, is_admin=is_admin,
                          error="Já existe um usuário com esse login.", status=409)
    except Invalid as e:
        return _user_form(request, mode="add", login=login, is_admin=is_admin,
                          error=str(e), status=400)
    raise web.HTTPSeeOther("/users")


async def users_edit_get(request: web.Request):
    _require_admin(request)
    login = request.match_info["login"]
    user = await request.app[STORE].get_user(login)
    if user is None:
        raise NotFound(login)
    return _user_form(request, mode="edit", login=login, is_admin=user.is_admin)


async def users_edit_post(request: web.Request):
    p = _require_admin(request)
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    login = request.match_info["login"]
    password = _text(form.get("password"))
    vfs = request.app[VFS]
    is_admin = "is_admin" in form or login == vfs.admin_login
    if login == p.login and not is_admin:
        return _user_form(request, mode="edit", login=login, is_admin=True,
                          error="Você não pode remover o próprio acesso de admin.", status=400)
    try:
        await vfs.update_user(login, password or None, is_admin)
    except Invalid as e:
        return _user_form(request, mode="edit", login=login, is_admin=is_admin, error=str(e), status=400)
    raise web.HTTPSeeOther("/users")


async def users_delete_post(request: web.Request):
    p = _require_admin(request)
    form = await request.post()
    _check_csrf(request, form.get("csrf"))
    login = request.match_info["login"]
    vfs = request.app[VFS]
    if login == p.login:
        return await _render_users(request, "Você não pode apagar a própria conta.", 400)
    if login == vfs.admin_login:
        return await _render_users(request, "O admin principal não pode ser removido.", 403)
    await vfs.delete_user(login, delete_files="delete_files" in form)
    raise web.HTTPSeeOther("/users")


# ---------------- montagem ----------------
def create_app(vfs: NebulaVFS, store: Store, settings: Settings) -> web.Application:
    app = web.Application(middlewares=[_middleware])
    app[VFS] = vfs
    app[STORE] = store
    app[SETTINGS] = settings
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        filters={"filesize": _filesize, "dt": _dt},
    )
    r = app.router
    r.add_get("/", index)
    r.add_get("/login", login_get)
    r.add_post("/login", login_post)
    r.add_post("/logout", logout_post)
    r.add_get("/files", files_get)
    r.add_post("/files/mkdir", mkdir_post)
    r.add_post("/files/upload", upload_post)
    r.add_post("/files/rename", rename_post)
    r.add_post("/files/delete", delete_post)
    r.add_get("/files/download", download_get)
    r.add_get("/files/stream", stream_get)
    r.add_get("/files/play", play_get)
    r.add_get("/users", users_get)
    r.add_get("/users/add", users_add_get)
    r.add_post("/users/add", users_add_post)
    r.add_get("/users/edit/{login}", users_edit_get)
    r.add_post("/users/edit/{login}", users_edit_post)
    r.add_post("/users/delete/{login}", users_delete_post)
    return app
