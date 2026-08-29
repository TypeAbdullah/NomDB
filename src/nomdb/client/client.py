"""
NomDB Official Client Library (Synchronous and Asynchronous).
Communicates exclusively over TCP using the RESP protocol.
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from nomdb.client.pool import SyncConnection, AsyncConnection
from nomdb.protocol.resp import ErrorResponse, SimpleString
from nomdb.protocol.exceptions import NomDBError


class SyncPipeline:
    """Synchronous pipeline for batching requests without waiting for intermediate responses."""

    def __init__(self, client: Client):
        self.client = client
        self.commands: List[Tuple[Any, ...]] = []

    def set(self, key: str, value: Any, **kwargs) -> SyncPipeline:
        parts = ["SET", key, value]
        if kwargs.get("ex"):
            parts.extend(["EX", kwargs["ex"]])
        if kwargs.get("px"):
            parts.extend(["PX", kwargs["px"]])
        if kwargs.get("nx"):
            parts.append("NX")
        if kwargs.get("xx"):
            parts.append("XX")
        self.commands.append(tuple(parts))
        return self

    def get(self, key: str) -> SyncPipeline:
        self.commands.append(("GET", key))
        return self

    def incr(self, key: str) -> SyncPipeline:
        self.commands.append(("INCR", key))
        return self

    def hset(self, key: str, field: str, value: Any) -> SyncPipeline:
        self.commands.append(("HSET", key, field, value))
        return self

    def execute(self) -> List[Any]:
        if not self.commands:
            return []
        conn = self.client._conn
        if not conn.sock:
            conn.connect()

        # Send all commands in one TCP burst
        from nomdb.protocol.encoder import RESPEncoder
        payloads = [RESPEncoder.encode_command(*cmd) for cmd in self.commands]
        conn.sock.sendall(b"".join(payloads))

        results = []
        while len(results) < len(self.commands):
            cmds = conn.parser.get_parsed_commands()
            results.extend(cmds)
            if len(results) >= len(self.commands):
                break
            chunk = conn.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Connection closed during pipeline")
            conn.parser.feed(chunk)

        self.commands.clear()
        return results[:len(payloads)]


class Client:
    """Official synchronous NomDB Client."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, timeout: float = 10.0):
        self.host = host
        self.port = port
        self._conn = SyncConnection(host, port, timeout)

    def execute_command(self, *args: Any) -> Any:
        res = self._conn.execute(*args)
        if isinstance(res, ErrorResponse):
            raise NomDBError(res.message, prefix=res.prefix)
        return res

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def ping(self, message: Optional[str] = None) -> Any:
        return self.execute_command("PING", *( [message] if message else [] ))

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
        get: bool = False,
    ) -> Any:
        parts = ["SET", key, value]
        if ex is not None:
            parts.extend(["EX", ex])
        if px is not None:
            parts.extend(["PX", px])
        if nx:
            parts.append("NX")
        if xx:
            parts.append("XX")
        if get:
            parts.append("GET")
        return self.execute_command(*parts)

    def get(self, key: str) -> Optional[bytes]:
        return self.execute_command("GET", key)

    def delete(self, *keys: str) -> int:
        return self.execute_command("DEL", *keys)

    def exists(self, *keys: str) -> int:
        return self.execute_command("EXISTS", *keys)

    def incr(self, key: str) -> int:
        return self.execute_command("INCR", key)

    def incrby(self, key: str, amount: int) -> int:
        return self.execute_command("INCRBY", key, amount)

    def decr(self, key: str) -> int:
        return self.execute_command("DECR", key)

    def decrby(self, key: str, amount: int) -> int:
        return self.execute_command("DECRBY", key, amount)

    # Hashes
    def hset(self, key: str, field: Optional[str] = None, value: Optional[Any] = None, mapping: Optional[Dict[str, Any]] = None) -> int:
        parts = ["HSET", key]
        if mapping:
            for f, v in mapping.items():
                parts.extend([f, v])
        elif field is not None and value is not None:
            parts.extend([field, value])
        return self.execute_command(*parts)

    def hget(self, key: str, field: str) -> Optional[bytes]:
        return self.execute_command("HGET", key, field)

    def hgetall(self, key: str) -> Dict[bytes, bytes]:
        flat = self.execute_command("HGETALL", key)
        res = {}
        for i in range(0, len(flat), 2):
            res[flat[i]] = flat[i + 1]
        return res

    def hdel(self, key: str, *fields: str) -> int:
        return self.execute_command("HDEL", key, *fields)

    # Lists
    def lpush(self, key: str, *values: Any) -> int:
        return self.execute_command("LPUSH", key, *values)

    def rpush(self, key: str, *values: Any) -> int:
        return self.execute_command("RPUSH", key, *values)

    def lpop(self, key: str, count: Optional[int] = None) -> Any:
        return self.execute_command("LPOP", key, *( [count] if count is not None else [] ))

    def rpop(self, key: str, count: Optional[int] = None) -> Any:
        return self.execute_command("RPOP", key, *( [count] if count is not None else [] ))

    def lrange(self, key: str, start: int, stop: int) -> List[bytes]:
        return self.execute_command("LRANGE", key, start, stop)

    # Sets
    def sadd(self, key: str, *members: Any) -> int:
        return self.execute_command("SADD", key, *members)

    def srem(self, key: str, *members: Any) -> int:
        return self.execute_command("SREM", key, *members)

    def smembers(self, key: str) -> List[bytes]:
        return self.execute_command("SMEMBERS", key)

    def sismember(self, key: str, member: Any) -> int:
        return self.execute_command("SISMEMBER", key, member)

    # Sorted Sets
    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        parts = ["ZADD", key]
        for m, score in mapping.items():
            parts.extend([score, m])
        return self.execute_command(*parts)

    def zscore(self, key: str, member: str) -> Optional[float]:
        res = self.execute_command("ZSCORE", key, member)
        return float(res) if res is not None else None

    def zrank(self, key: str, member: str) -> Optional[int]:
        return self.execute_command("ZRANK", key, member)

    def zrange(self, key: str, start: int, stop: int, withscores: bool = False) -> List[Any]:
        args = ["ZRANGE", key, start, stop]
        if withscores:
            args.append("WITHSCORES")
        return self.execute_command(*args)

    def pipeline(self) -> SyncPipeline:
        return SyncPipeline(self)


class AsyncClient:
    """Official asynchronous NomDB Client using asyncio."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        self.host = host
        self.port = port
        self._conn = AsyncConnection(host, port)

    async def execute_command(self, *args: Any) -> Any:
        res = await self._conn.execute(*args)
        if isinstance(res, ErrorResponse):
            raise NomDBError(res.message, prefix=res.prefix)
        return res

    async def close(self) -> None:
        await self._conn.close()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def ping(self, message: Optional[str] = None) -> Any:
        return await self.execute_command("PING", *( [message] if message else [] ))

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> Any:
        parts = ["SET", key, value]
        if ex is not None:
            parts.extend(["EX", ex])
        if px is not None:
            parts.extend(["PX", px])
        if nx:
            parts.append("NX")
        if xx:
            parts.append("XX")
        return await self.execute_command(*parts)

    async def get(self, key: str) -> Optional[bytes]:
        return await self.execute_command("GET", key)

    async def delete(self, *keys: str) -> int:
        return await self.execute_command("DEL", *keys)

    async def incr(self, key: str) -> int:
        return await self.execute_command("INCR", key)
