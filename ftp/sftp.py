import asyncssh
import asyncio
from typing import Any, List, Optional, Union
import logging
import os
from pathlib import PurePosixPath
from ftp.pathio import MongoDBPathIO

logger = logging.getLogger("NebulaFTP.SFTP")

class NebulaSFTPFile:
    def __init__(self, sftp_server, file_obj, path_io):
        self._server = sftp_server
        self._file = file_obj
        self._path_io = path_io

    async def read(self, size: int = -1, offset: int = 0) -> bytes:
        if hasattr(self._file, 'read'):
            res = self._file.read(size if size > 0 else -1)
            if asyncio.iscoroutine(res):
                return await res
            return res
        raise NotImplementedError("Download streaming via SFTP is not natively supported by this architecture yet. Use the Web UI/NebulaStream for downloads.")

    async def write(self, data: bytes, offset: int = 0) -> int:
        if hasattr(self._file, 'write'):
            res = self._file.write(data)
            if asyncio.iscoroutine(res):
                await res
            return len(data)
        raise NotImplementedError("Upload object does not support write()")

    async def close(self) -> None:
        if hasattr(self._file, 'close'):
            res = self._file.close()
            if asyncio.iscoroutine(res):
                await res

class NebulaSFTPServer(asyncssh.SFTPServer):
    def __init__(self, conn, user, path_io_nursery):
        self._conn = conn
        self._user = user
        self._path_io = path_io_nursery(user)
        super().__init__(conn)

    async def realpath(self, path: Union[str, bytes]) -> str:
        if isinstance(path, bytes):
            path = path.decode('utf-8')
        path = path.strip()
        if not path or path == '.':
            return '/'
        return path if path.startswith('/') else f'/{path}'

    async def _resolve(self, path: Union[str, bytes]):
        path = await self.realpath(path)

        p = PurePosixPath(path)
        permission = self._user.get_permissions(str(p))
        if not permission.readable and not permission.writable:
             raise asyncssh.SFTPPermissionDenied("Permission denied")

        return p

    async def stat(self, path: Union[str, bytes], flags: int = 0) -> asyncssh.SFTPAttrs:
        p = await self._resolve(path)
        try:
            stat_info = await self._path_io.stat(p)
            attrs = asyncssh.SFTPAttrs(
                size=stat_info.st_size,
                permissions=stat_info.st_mode,
                atime=int(stat_info.st_mtime), # Mapping mtime to atime as atime is missing in MongoDBPathIO
                mtime=int(stat_info.st_mtime)
            )
            return attrs
        except Exception as e:
            raise asyncssh.SFTPNoSuchFile(f"No such file: {path}")

    async def lstat(self, path: Union[str, bytes], flags: int = 0) -> asyncssh.SFTPAttrs:
        return await self.stat(path, flags)

    async def opendir(self, path: Union[str, bytes]) -> Any:
        p = await self._resolve(path)
        try:
            items = []
            async for item in self._path_io.list(p):
                stat_info = await self._path_io.stat(p / item)
                attrs = asyncssh.SFTPAttrs(
                    size=stat_info.st_size,
                    permissions=stat_info.st_mode,
                    atime=int(stat_info.st_mtime),
                    mtime=int(stat_info.st_mtime)
                )
                items.append(asyncssh.SFTPName(item, attrs=attrs))
            return items
        except Exception as e:
            raise asyncssh.SFTPNoSuchFile(f"No such directory: {path}")

    async def readdir(self, handle: Any) -> List[asyncssh.SFTPName]:
        if isinstance(handle, list):
            items = handle[:]
            handle.clear()
            return items
        return []

    async def open(self, path: Union[str, bytes], pflags: int, attrs: asyncssh.SFTPAttrs) -> Any:
        p = await self._resolve(path)

        mode = "rb"
        if pflags & asyncssh.FXF_WRITE:
            mode = "wb"
            if pflags & asyncssh.FXF_APPEND:
                mode = "ab"

        try:
            f = await self._path_io.open(p, mode)
            return NebulaSFTPFile(self, f, self._path_io)
        except Exception as e:
            raise asyncssh.SFTPFailure(f"Failed to open {path}: {str(e)}")

    async def mkdir(self, path: Union[str, bytes], attrs: asyncssh.SFTPAttrs) -> None:
        p = await self._resolve(path)
        try:
            await self._path_io.mkdir(p)
        except Exception as e:
            raise asyncssh.SFTPFailure(str(e))

    async def rmdir(self, path: Union[str, bytes]) -> None:
        p = await self._resolve(path)
        try:
            await self._path_io.rmdir(p)
        except Exception as e:
            raise asyncssh.SFTPFailure(str(e))

    async def remove(self, path: Union[str, bytes]) -> None:
        p = await self._resolve(path)
        try:
            await self._path_io.unlink(p) # PathIO uses unlink for file removal
        except Exception as e:
            raise asyncssh.SFTPFailure(str(e))

    async def rename(self, oldpath: Union[str, bytes], newpath: Union[str, bytes]) -> None:
        p1 = await self._resolve(oldpath)
        p2 = await self._resolve(newpath)
        try:
            await self._path_io.rename(p1, p2)
        except Exception as e:
            raise asyncssh.SFTPFailure(str(e))

class NebulaSSHServer(asyncssh.SSHServer):
    def __init__(self, user_manager, path_io_nursery):
        self.user_manager = user_manager
        self.path_io_nursery = path_io_nursery
        self._user = None
        self._user_info = None

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        logger.info(f"SFTP connection received from {conn.get_extra_info('peername')}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.info("SFTP connection lost")
        if self._user_info:
            asyncio.create_task(self.user_manager.notify_logout(self._user_info))

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        state, user, info = await self.user_manager.get_user(username)
        # Store user info for cleanup in connection_lost even if authentication fails
        self._user_info = user
        if user and await self.user_manager.authenticate(user, password):
            self._user = user
            return True
        return False

    def session_requested(self) -> bool:
        return True

async def start_sftp_server(user_manager, path_io_nursery, host='0.0.0.0', port=2222):
    key_path = "sftp_host_key"
    if not os.path.exists(key_path):
        logger.info("Generating new SFTP host key...")
        server_key = asyncssh.generate_private_key('ssh-rsa')
        server_key.write_private_key(key_path)
    else:
        logger.info("Loading existing SFTP host key...")
        server_key = asyncssh.read_private_key(key_path)

    def server_factory():
        return NebulaSSHServer(user_manager, path_io_nursery)

    def sftp_factory(conn):
        ssh_server = conn.get_server_object()
        user = ssh_server._user
        return NebulaSFTPServer(conn, user, path_io_nursery)

    logger.info(f"🚀 Iniciando servidor SFTP em {host}:{port}")
    await asyncssh.create_server(
        server_factory, host, port,
        server_host_keys=[server_key],
        sftp_factory=sftp_factory
    )
