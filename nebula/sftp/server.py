"""Adaptador SFTP: traduz chamadas do asyncssh para o NebulaVFS. Nada aqui toca o disco do host.

Cada sessão SFTP recebe o Principal do usuário autenticado. O VFS é quem decide o que ele vê
(usuário comum: a própria pasta vira '/'; admin: a raiz real).
"""
from __future__ import annotations

import logging
import shutil
import os
import posixpath
import stat as statmod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterator

import asyncssh
from asyncssh.constants import (
    ACE4_APPEND_DATA, ACE4_WRITE_DATA, FXF_ACCESS_DISPOSITION,
    FXF_APPEND_DATA, FXF_APPEND, FXF_CREAT, FXF_CREATE_NEW, FXF_CREATE_TRUNCATE,
    FXF_EXCL, FXF_OPEN_OR_CREATE, FXF_TRUNC, FXF_TRUNCATE_EXISTING, FXF_WRITE,
)

from .. import security
from ..vfs import (
    Denied, Exists, FSError, Invalid, IsADir, NebulaVFS, NotADir, NotEmpty,
    NotFound, Principal, ReadHandle, Stat, WriteHandle,
)

log = logging.getLogger("nebula.sftp")

_DIR_MODE = statmod.S_IFDIR | 0o755
_FILE_MODE = statmod.S_IFREG | 0o644


# ---------------- erros ----------------
def _sftp_error(e: Exception) -> asyncssh.SFTPError:
    reason = str(e) or type(e).__name__
    if isinstance(e, NotFound):
        return asyncssh.SFTPNoSuchFile(reason)
    if isinstance(e, Exists):
        return asyncssh.SFTPFileAlreadyExists(reason)
    if isinstance(e, Denied):
        return asyncssh.SFTPPermissionDenied(reason)
    if isinstance(e, NotEmpty):
        return asyncssh.SFTPDirNotEmpty(reason)
    if isinstance(e, NotADir):
        return asyncssh.SFTPNotADirectory(reason)
    if isinstance(e, IsADir):
        return asyncssh.SFTPFileIsADirectory(reason)
    if isinstance(e, Invalid):
        return asyncssh.SFTPInvalidParameter(reason)
    return asyncssh.SFTPFailure(reason)


@contextmanager
def _vfs_errors() -> Iterator[None]:
    """Converte erros do núcleo em erros SFTP. Caminho que sai da raiz vira 'negado'."""
    try:
        yield
    except security.PathError as e:
        raise asyncssh.SFTPPermissionDenied(str(e)) from e
    except FSError as e:
        raise _sftp_error(e) from e
    except asyncssh.SFTPError:
        raise
    except Exception as e:  # erro inesperado: registra para diagnóstico e devolve falha ao cliente
        log.exception("erro interno no SFTP")
        raise asyncssh.SFTPFailure(f"erro interno: {type(e).__name__}: {e}") from e


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    # Alguns clientes Windows mandam o nome na página de código local (cp1252), não em UTF-8.
    try:
        text = raw.decode("cp1252")
    except UnicodeDecodeError:
        raise asyncssh.SFTPInvalidParameter("caminho não é UTF-8 nem cp1252") from None
    log.warning("cliente enviou caminho fora de UTF-8; interpretado como cp1252: %r", text)
    return text


@dataclass
class _OpenFile:
    """Arquivo aberto numa sessão SFTP (o objeto que o asyncssh guarda como handle)."""
    vpath: str
    handle: ReadHandle | WriteHandle
    writable: bool


# ---------------- servidor SFTP ----------------
class NebulaSFTPServer(asyncssh.SFTPServer):
    """Uma sessão SFTP de um usuário autenticado. Todo acesso passa pelo NebulaVFS."""

    def __init__(self, chan, vfs: NebulaVFS, principal: Principal):
        super().__init__(chan)
        self._vfs = vfs
        self._p = principal

    # --- helpers ---
    def _vpath(self, raw: bytes) -> str:
        """Caminho do cliente, já normalizado (raiz do usuário = '/'). Sem tocar no disco."""
        text = _decode(raw)
        try:
            return security.normalize(text)
        except security.PathError as e:
            raise asyncssh.SFTPPermissionDenied(str(e)) from e

    def _attrs(self, st: Stat) -> asyncssh.SFTPAttrs:
        return asyncssh.SFTPAttrs(
            size=0 if st.is_dir else st.size,
            uid=0,
            gid=0,
            permissions=_DIR_MODE if st.is_dir else _FILE_MODE,
            atime=int(st.mtime),
            mtime=st.mtime,
        )

    # --- nomes e formato (sem consultar usuários do host) ---
    def format_user(self, uid) -> str:
        return "nebula"

    def format_group(self, gid) -> str:
        return "nebula"

    # --- abrir / fechar / ler / gravar ---
    async def open(self, path: bytes, pflags: int, attrs) -> _OpenFile:
        vpath = self._vpath(path)
        with _vfs_errors():
            if not pflags & FXF_WRITE:
                h = await self._vfs.open_read(self._p, vpath)
                return _OpenFile(vpath, h, writable=False)
            h = await self._vfs.open_write(
                self._p, vpath,
                truncate=bool(pflags & FXF_TRUNC),
                append=bool(pflags & FXF_APPEND),
                create=bool(pflags & FXF_CREAT),
                exclusive=bool(pflags & FXF_EXCL),
            )
            return _OpenFile(vpath, h, writable=True)

    async def open56(self, path: bytes, desired_access: int, flags: int, attrs) -> _OpenFile:
        """SFTPv5+: mesma regra do open(), com os bits de acesso e de disposição do protocolo."""
        vpath = self._vpath(path)
        disposition = flags & FXF_ACCESS_DISPOSITION
        writable = bool(desired_access & (ACE4_WRITE_DATA | ACE4_APPEND_DATA))
        with _vfs_errors():
            if not writable:
                h = await self._vfs.open_read(self._p, vpath)
                return _OpenFile(vpath, h, writable=False)
            h = await self._vfs.open_write(
                self._p, vpath,
                truncate=disposition in (FXF_CREATE_TRUNCATE, FXF_TRUNCATE_EXISTING),
                append=bool(flags & FXF_APPEND_DATA) or bool(desired_access & ACE4_APPEND_DATA),
                create=disposition in (FXF_OPEN_OR_CREATE, FXF_CREATE_NEW, FXF_CREATE_TRUNCATE),  # TRUNCATE_EXISTING não cria
                exclusive=disposition == FXF_CREATE_NEW,
            )
            return _OpenFile(vpath, h, writable=True)

    async def read(self, file_obj: _OpenFile, offset: int, size: int) -> bytes:
        with _vfs_errors():  # WriteHandle também lê (abertura r+/w+ do RaiDrive e do Explorer)
            return await file_obj.handle.read(offset, size)

    async def write(self, file_obj: _OpenFile, offset: int, data: bytes) -> int:
        if not file_obj.writable:
            raise asyncssh.SFTPPermissionDenied("arquivo aberto só para leitura")
        with _vfs_errors():
            return await file_obj.handle.write(data, offset)

    async def close(self, file_obj: _OpenFile) -> None:
        with _vfs_errors():
            await file_obj.handle.close()

    # --- atributos ---
    async def stat(self, path: bytes) -> asyncssh.SFTPAttrs:
        vpath = self._vpath(path)
        with _vfs_errors():
            return self._attrs(await self._vfs.stat(self._p, vpath))

    async def lstat(self, path: bytes) -> asyncssh.SFTPAttrs:
        return await self.stat(path)

    async def fstat(self, file_obj: _OpenFile) -> asyncssh.SFTPAttrs:
        with _vfs_errors():
            st = await self._vfs.stat(self._p, file_obj.vpath)
        attrs = self._attrs(st)
        if file_obj.writable:
            attrs.size = file_obj.handle.size()
        else:
            attrs.size = file_obj.handle.size
        return attrs

    async def setstat(self, path: bytes, attrs: asyncssh.SFTPAttrs) -> None:
        vpath = self._vpath(path)
        with _vfs_errors():
            await self._vfs.stat(self._p, vpath)  # existe e é visível para este usuário
            if attrs.mtime is not None:
                await self._vfs.set_mtime(self._p, vpath, float(attrs.mtime))
        # size: só trunca via handle aberto (fsetstat); permissões e donos são ignorados

    async def lsetstat(self, path: bytes, attrs: asyncssh.SFTPAttrs) -> None:
        await self.setstat(path, attrs)

    async def fsetstat(self, file_obj: _OpenFile, attrs: asyncssh.SFTPAttrs) -> None:
        with _vfs_errors():
            if attrs.size is not None and file_obj.writable:
                await file_obj.handle.truncate_to(int(attrs.size))
            if attrs.mtime is not None:
                await self._vfs.set_mtime(self._p, file_obj.vpath, float(attrs.mtime))

    # --- diretórios ---
    async def scandir(self, path: bytes) -> AsyncIterator[asyncssh.SFTPName]:
        vpath = self._vpath(path)
        with _vfs_errors():
            here = await self._vfs.stat(self._p, vpath)
            if not here.is_dir:
                raise asyncssh.SFTPNotADirectory(vpath)
            parent = posixpath.dirname(vpath) or "/"
            parent_st = await self._vfs.stat(self._p, parent)
            children = await self._vfs.listdir(self._p, vpath)

        yield self._entry(b".", self._attrs(here))
        yield self._entry(b"..", self._attrs(parent_st))
        for st in children:
            yield self._entry(st.name.encode("utf-8"), self._attrs(st))

    def _entry(self, name: bytes, attrs: asyncssh.SFTPAttrs) -> asyncssh.SFTPName:
        entry = asyncssh.SFTPName(name, attrs=attrs)
        self.format_longname(entry)
        return entry

    async def mkdir(self, path: bytes, attrs: asyncssh.SFTPAttrs) -> None:
        vpath = self._vpath(path)
        with _vfs_errors():
            await self._vfs.mkdir(self._p, vpath)

    async def rmdir(self, path: bytes) -> None:
        vpath = self._vpath(path)
        with _vfs_errors():
            await self._vfs.rmdir(self._p, vpath)

    async def remove(self, path: bytes) -> None:
        vpath = self._vpath(path)
        with _vfs_errors():
            await self._vfs.remove(self._p, vpath)

    # --- renomear ---
    async def rename(self, oldpath: bytes, newpath: bytes) -> None:
        await self._rename(oldpath, newpath, overwrite=False)

    async def posix_rename(self, oldpath: bytes, newpath: bytes) -> None:
        await self._rename(oldpath, newpath, overwrite=True)

    async def _rename(self, oldpath: bytes, newpath: bytes, overwrite: bool) -> None:
        src = self._vpath(oldpath)
        dst = self._vpath(newpath)
        with _vfs_errors():
            await self._vfs.rename(self._p, src, dst, overwrite=overwrite)

    # --- caminho ---
    def realpath(self, path: bytes) -> bytes:
        return self._vpath(path).encode("utf-8")

    # --- não suportado: rejeitado com SFTPOpUnsupported (nada cai no disco) ---
    def readlink(self, path: bytes):
        raise asyncssh.SFTPOpUnsupported("links simbólicos não são suportados")

    def symlink(self, oldpath: bytes, newpath: bytes):
        raise asyncssh.SFTPOpUnsupported("links simbólicos não são suportados")

    def link(self, oldpath: bytes, newpath: bytes):
        raise asyncssh.SFTPOpUnsupported("links físicos não são suportados")

    def lock(self, file_obj, offset: int, length: int, flags: int):
        raise asyncssh.SFTPOpUnsupported("bloqueio de arquivo não é suportado")

    def unlock(self, file_obj, offset: int, length: int):
        raise asyncssh.SFTPOpUnsupported("bloqueio de arquivo não é suportado")

    def statvfs(self, path: bytes) -> asyncssh.SFTPVFSAttrs:
        """Espaço livre = disco local do staging (é ele que limita o próximo upload). RaiDrive consulta isso."""
        try:
            du = shutil.disk_usage(self._vfs.blobs.staging_dir)
            total, free = du.total, du.free
        except OSError:
            total = free = 1 << 40
        bs = 4096
        return asyncssh.SFTPVFSAttrs(
            bsize=bs, frsize=bs, blocks=total // bs, bfree=free // bs, bavail=free // bs,
            files=1 << 30, ffree=1 << 30, favail=1 << 30, fsid=0, flags=0, namemax=255,
        )

    def fstatvfs(self, file_obj) -> asyncssh.SFTPVFSAttrs:
        return self.statvfs(b"/")

    def fsync(self, file_obj):
        raise asyncssh.SFTPOpUnsupported("fsync não é suportado")

    def exit(self) -> None:
        return None


# ---------------- servidor SSH ----------------
class _NebulaSSHServer(asyncssh.SSHServer):
    """Autenticação por senha pelo VFS. Só o subsistema SFTP é liberado (sem shell nem exec)."""

    def __init__(self, vfs: NebulaVFS):
        self._vfs = vfs
        self._ip = ""

    def connection_made(self, conn) -> None:
        peer = conn.get_extra_info("peername")
        self._ip = peer[0] if peer else ""

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        principal = await self._vfs.authenticate(username, password, ip=self._ip)
        if principal is None:
            log.warning("login SFTP recusado para %r", username)
            return False
        log.info("login SFTP aceito: %s", principal.login)
        return True


async def _load_principal(vfs: NebulaVFS, conn) -> Principal:
    login = conn.get_extra_info("username")
    user = await vfs.store.get_user(login) if login else None
    if user is None:
        raise asyncssh.SFTPPermissionDenied("usuário não existe mais")
    return Principal(user.login, user.is_admin)


def _ensure_host_key(host_key_path: str) -> None:
    path = Path(host_key_path)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    key = asyncssh.generate_private_key("ssh-ed25519")
    key.write_private_key(str(path))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    log.info("chave de host SSH criada em %s", path)


async def start_sftp_server(vfs: NebulaVFS, host: str, port: int, host_key_path) -> asyncssh.SSHAcceptor:
    _ensure_host_key(str(host_key_path))
    # No Windows o asyncssh só anuncia statvfs se existir os.statvfs; nosso statvfs é virtual.
    try:
        from asyncssh.sftp import SFTPServerHandler

        for ext in ((b"statvfs@openssh.com", b"2"), (b"fstatvfs@openssh.com", b"2")):
            if ext not in SFTPServerHandler._extensions:
                SFTPServerHandler._extensions.append(ext)
        # ranges@asyncssh.com exige seek(SEEK_DATA) no objeto de arquivo; nossos arquivos são virtuais
        SFTPServerHandler._extensions[:] = [
            e for e in SFTPServerHandler._extensions if e[0] != b"ranges@asyncssh.com"
        ]
    except Exception:  # pragma: no cover
        pass

    async def sftp_factory(chan) -> NebulaSFTPServer:
        conn = chan.get_connection()
        principal = await _load_principal(vfs, conn)
        return NebulaSFTPServer(chan, vfs, principal)

    return await asyncssh.listen(
        host, port,
        server_factory=lambda: _NebulaSSHServer(vfs),
        server_host_keys=[str(host_key_path)],
        password_auth=True,
        public_key_auth=False,
        kbdint_auth=False,
        process_factory=None,
        sftp_factory=sftp_factory,
        allow_scp=False,
    )
