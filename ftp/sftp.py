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

    async def seek(self, offset: int = 0) -> None:
        if hasattr(self._file, 'seek'):
            res = self._file.seek(offset)
            if asyncio.iscoroutine(res):
                await res

    async def read(self, size: int = -1, offset: int = 0) -> bytes:
        await self.seek(offset)
        if hasattr(self._file, 'read'):
            res = self._file.read(size if size > 0 else -1)
            if asyncio.iscoroutine(res):
                return await res
            return res

        if hasattr(self._file, 'iter_by_block'):
            read_size = size if size > 0 else (1024 * 1024)
            chunks = []
            total_read = 0

            async for chunk in self._file.iter_by_block(read_size):
                if not chunk:
                    break

                needed = size - total_read if size > 0 else len(chunk)
                if len(chunk) > needed:
                    chunks.append(chunk[:needed])
                    total_read += needed
                    break
                else:
                    chunks.append(chunk)
                    total_read += len(chunk)

                if size > 0 and total_read >= size:
                    break

            return b"".join(chunks)

        raise NotImplementedError("Download streaming via SFTP is not natively supported by this architecture yet. Use the Web UI/NebulaStream for downloads.")

    async def write(self, data: bytes, offset: int = 0) -> int:
        await self.seek(offset)
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
            path = path.decode('utf-8', errors='replace')
        path = path.strip()
        if not path:
            return '/'
        posix_path = path if path.startswith('/') else f'/{path}'
        normalized = os.path.normpath(posix_path).replace('\\', '/')
        if not normalized.startswith('/'):
            normalized = '/' + normalized
        return normalized

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

    async def scandir(self, path: Union[str, bytes]):
        p = await self._resolve(path)
        try:
            if hasattr(self._path_io, "listdir"):
                names = await self._path_io.listdir(p)
            elif hasattr(self._path_io, "list"):
                res = self._path_io.list(p)
                if asyncio.iscoroutine(res):
                    names = await res
                else:
                    names = [item async for item in res]
            else:
                names = []

            for item in names:
                item_bytes = item.encode('utf-8') if isinstance(item, str) else item
                try:
                    stat_info = await self._path_io.stat(p / item)
                    attrs = asyncssh.SFTPAttrs(
                        size=stat_info.st_size,
                        permissions=stat_info.st_mode,
                        atime=int(stat_info.st_mtime),
                        mtime=int(stat_info.st_mtime)
                    )
                except Exception:
                    attrs = asyncssh.SFTPAttrs()
                yield asyncssh.SFTPName(item_bytes, attrs=attrs)
        except Exception as e:
            logger.error(f"SFTP scandir error on {path}: {e}")
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
        logger.info(f"SFTP connection lost: {exc}")
        if self._user_info:
            asyncio.create_task(self.user_manager.notify_logout(self._user_info))

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        try:
            state, user, info = await self.user_manager.get_user(username)
            self._user_info = user
            if user:
                authenticated = await self.user_manager.authenticate(user, password)
                logger.info(f"SFTP validate_password for '{username}': auth={authenticated}, user.pass={user.password}")
                if authenticated:
                    self._user = user
                    return True
            else:
                logger.warning(f"SFTP validate_password for '{username}': user not found (state={state}, info={info})")
            return False
        except Exception as e:
            logger.error(f"SFTP validate_password exception for '{username}': {e}", exc_info=True)
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
        conn_obj = conn.get_connection() if hasattr(conn, 'get_connection') else conn
        ssh_server = getattr(conn_obj, '_owner', None)
        if not ssh_server and hasattr(conn_obj, 'get_server_object'):
            ssh_server = conn_obj.get_server_object()
        user = getattr(ssh_server, '_user', None) if ssh_server else None
        logger.info(f"sftp_factory created for user: {user.login if user else None}")
        return NebulaSFTPServer(conn, user, path_io_nursery)

    logger.info(f"🚀 Iniciando servidor SFTP em {host}:{port}")
    server = await asyncssh.create_server(
        server_factory, host, port,
        server_host_keys=[server_key],
        sftp_factory=sftp_factory
    )
    await server.wait_closed()
