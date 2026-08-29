# NomDB ⚡

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-53%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **NomDB** is a production-grade Redis-inspired in-memory key-value database built **from scratch in pure Python using asyncio**.
> It features a native RESP streaming protocol engine, custom SkipList-backed Sorted Sets, active min-heap expiration, dual persistence (AOF + Snapshots) with crash recovery, optimistic concurrency transactions (MULTI/EXEC/WATCH), Pub/Sub, primary-replica replication with circular backlog PSYNC, 16,384-slot clustering, an interactive CLI REPL, a Python client SDK, and a high-concurrency benchmark suite.

---

## 🏗 Architecture

```
NomDB (TCP Server)
│
├── Networking (asyncio TCP Server, Client Connection Pool, Idle Timeouts)
├── Protocol Engine (Streaming RESP2/RESP3 Parser & Encoder, Zero-Copy Buffer)
├── Command Dispatcher (Router, Dynamic Registry, Arity & Type Validation)
├── In-Memory Storage Engine
│   ├── Keyspace (Metadata, TTL, LRU/LFU Clocks, Modification Versioning)
│   ├── Strings (Raw bytes, atomic numeric INCR/DECR, subrange slicing)
│   ├── Hashes (Field-value dictionary mappings, numeric field increments)
│   ├── Lists (Double-ended fast deque with positional inserts, trims, pops)
│   ├── Sets (Hash sets with O(1) membership, union, intersection, diff)
│   └── Sorted Sets (Pure Python SkipList + Dict Index with O(log N) rank/range)
├── Expiration Engine (Lazy on-access check + Active Min-Heap sampling worker)
├── Memory Manager (Memory tracker, maxmemory limits, LRU & LFU evictions)
├── Persistence Engine
│   ├── Append-Only File (AOF with always, everysec, and no fsync + rewriting)
│   ├── Binary Snapshots (Compact RDB-style file with SHA-256 checksums)
│   └── Crash Recovery (AOF replay + truncated frame tolerance)
├── Transaction Layer (MULTI, EXEC, DISCARD, optimistic concurrency WATCH/UNWATCH)
├── Pub/Sub Broker (Channel subscriptions & glob pattern broadcast matching)
├── Replication Engine (Primary-replica stream, circular backlog ring buffer, PSYNC)
├── Cluster Engine (16,384 CRC16 hash slots, hash tag extraction, MOVED/ASK redirects)
├── Metrics & Observability (INFO sections, instantaneous ops/sec, Prometheus endpoint)
├── CLI REPL (nomdb-cli with color syntax, history, and multiline formatting)
└── Python Client SDK (nomdb.Client and AsyncClient with connection pooling and pipelining)
```

---

## 🚀 Quick Start

### 1. Installation

Clone and install editable package in Python 3.13+:

```bash
git clone https://github.com/your-username/NomDB.git
cd NomDB
pip install -e .
```

### 2. Start Database Server

```bash
nomdb-server --host 127.0.0.1 --port 6379
```

*(You can also use the `fluxkv-server` alias).*

### 3. Connect via Interactive CLI

```bash
nomdb-cli --host 127.0.0.1 --port 6379
```

```text
127.0.0.1:6379> SET name "Noman"
OK
127.0.0.1:6379> GET name
"Noman"
127.0.0.1:6379> INCR counter
(integer) 1
127.0.0.1:6379> HSET user:1 name "Noman" role "Architect"
(integer) 2
127.0.0.1:6379> HGETALL user:1
1) "name"
2) "Noman"
3) "role"
4) "Architect"
127.0.0.1:6379> ZADD leaderboard 100.0 "player1" 250.0 "player2" 50.0 "player3"
(integer) 3
127.0.0.1:6379> ZRANGE leaderboard 0 -1 WITHSCORES
1) "player3"
2) "50"
3) "player1"
4) "100"
5) "player2"
6) "250"
```

---

## 🐍 Python Client Library

Use the built-in TCP client:

### Synchronous Client

```python
from nomdb import Client

with Client(host="127.0.0.1", port=6379) as client:
    client.set("language", "Python")
    print(client.get("language"))  # b"Python"

    client.hset("user:100", mapping={"name": "Alice", "role": "Dev"})
    print(client.hgetall("user:100"))

    # Pipelining
    pipe = client.pipeline()
    pipe.set("a", 1).set("b", 2).get("a").get("b")
    results = pipe.execute()
    print(results)  # ['OK', 'OK', b'1', b'2']
```

### Asynchronous Client

```python
import asyncio
from nomdb import AsyncClient

async def main():
    async with AsyncClient(host="127.0.0.1", port=6379) as client:
        await client.set("async_key", "speed")
        val = await client.get("async_key")
        print(val)

asyncio.run(main())
```

---

## 📦 Supported Commands

| Category | Commands |
| :--- | :--- |
| **Strings** | `SET`, `GET`, `GETDEL`, `GETEX`, `GETSET`, `MGET`, `MSET`, `SETNX`, `INCR`, `INCRBY`, `INCRBYFLOAT`, `DECR`, `DECRBY`, `APPEND`, `STRLEN`, `SETRANGE`, `GETRANGE` |
| **Hashes** | `HSET`, `HGET`, `HMGET`, `HDEL`, `HEXISTS`, `HGETALL`, `HKEYS`, `HVALS`, `HLEN`, `HINCRBY`, `HINCRBYFLOAT`, `HSETNX` |
| **Lists** | `LPUSH`, `RPUSH`, `LPOP`, `RPOP`, `LRANGE`, `LLEN`, `LINDEX`, `LSET`, `LINSERT`, `LTRIM`, `LREM` |
| **Sets** | `SADD`, `SREM`, `SISMEMBER`, `SMISMEMBER`, `SMEMBERS`, `SCARD`, `SPOP`, `SRANDMEMBER`, `SUNION`, `SINTER`, `SDIFF` |
| **Sorted Sets** | `ZADD`, `ZREM`, `ZSCORE`, `ZRANK`, `ZREVRANK`, `ZRANGE`, `ZREVRANGE`, `ZCARD`, `ZCOUNT`, `ZINCRBY` |
| **Keys** | `DEL`, `EXISTS`, `EXPIRE`, `PEXPIRE`, `EXPIREAT`, `PEXPIREAT`, `TTL`, `PTTL`, `PERSIST`, `TYPE`, `RENAME`, `RENAMENX`, `KEYS`, `SCAN`, `DBSIZE`, `RANDOMKEY`, `FLUSHDB`, `FLUSHALL`, `SELECT` |
| **Server** | `PING`, `ECHO`, `INFO`, `CONFIG GET`, `CONFIG SET`, `TIME`, `COMMAND`, `SAVE`, `BGSAVE`, `SHUTDOWN`, `AUTH`, `MEMORY USAGE`, `MEMORY STATS`, `QUIT` |
| **Transactions** | `MULTI`, `EXEC`, `DISCARD`, `WATCH`, `UNWATCH` |
| **Pub/Sub** | `SUBSCRIBE`, `UNSUBSCRIBE`, `PSUBSCRIBE`, `PUNSUBSCRIBE`, `PUBLISH` |
| **Replication** | `REPLCONF`, `PSYNC`, `SYNC`, `REPLICAOF`, `SLAVEOF` |
| **Cluster** | `CLUSTER NODES`, `CLUSTER SLOTS`, `CLUSTER INFO`, `CLUSTER MEET`, `CLUSTER ADDSLOTS`, `CLUSTER KEYSLOT` |

---

## ⚡ Performance Benchmark

Run high-concurrency benchmarks across single and pipelined workloads:

```bash
nomdb-benchmark --host 127.0.0.1 --port 6379 -c 20 -n 10000 -P 16
```

### Measured Results

| Operation | Concurrency | Pipeline | Throughput | Latency (p50) | Latency (p99) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | 10 clients | 16 | **25,580 ops/sec** | 0.14 ms | 0.41 ms |
| **PING** | 5 clients | 1 | **5,840 ops/sec** | 0.62 ms | 3.97 ms |
| **SET** | 10 clients | 16 | **1,610 ops/sec** | 2.95 ms | 6.60 ms |

---

## 🧪 Running Tests

Execute the complete test suite (Unit, Integration, Persistence, Replication, Cluster, Fuzzing):

```bash
pytest -v
```

---

## 🐳 Docker Setup

Run Primary + Replica database cluster using Docker Compose:

```bash
docker compose up --build
```

---

## 💼 CV / Portfolio Description

> **NomDB — Redis-inspired in-memory database implemented from scratch in Python.** Built an asynchronous TCP server with RESP-compatible streaming protocol parser, native native data structures (Strings, Hashes, Lists, Sets, and custom SkipList-backed Sorted Sets with $O(\log N)$ rank/range operations), active min-heap expiration, LRU/LFU memory eviction, AOF and binary snapshot persistence with crash recovery, optimistic concurrency transactions (MULTI/EXEC/WATCH), Pub/Sub, pipelining, primary-replica replication with circular backlog PSYNC, 16,384-slot clustering, CLI REPL, and benchmark suite.
