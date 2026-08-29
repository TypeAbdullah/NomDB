<div align="center">

# ⚡ NomDB
### High-Performance In-Memory Key-Value Database & Server in Pure Python

[![PyPI Version](https://img.shields.io/pypi/v/nomdb?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/nomdb/)
[![Python Version](https://img.shields.io/badge/python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-56%20passed-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/TypeAbdullah/NomDB)
[![Read Speed](https://img.shields.io/badge/read%20speed-537k%20ops%2Fsec-6366f1?style=for-the-badge&logo=speedtest&logoColor=white)](https://github.com/TypeAbdullah/NomDB)
[![Latency](https://img.shields.io/badge/p50%20latency-0.0019%20ms-06b6d4?style=for-the-badge&logo=fastapi&logoColor=white)](https://github.com/TypeAbdullah/NomDB)
[![License](https://img.shields.io/badge/license-MIT-f59e0b?style=for-the-badge)](https://opensource.org/licenses/MIT)

<p align="center">
  <b>NomDB</b> is a Redis-inspired in-memory database built <b>from scratch using Python and asyncio</b>.<br/>
  Zero Redis wrappers. Zero C dependencies. Run as a <b>standalone TCP Server</b>, an <b>Embedded Library (<code>import nomdb</code>)</b>, or manage via the <b>Built-in Web Dashboard</b>.
</p>

</div>

---

## 🎯 Key Capabilities

* 🌐 **Full RESP2 / RESP3 Protocol Compatibility**: Works with standard Redis clients and the native NomDB SDK.
* 📦 **Three Flexible Execution Modes**:
  1. **Standalone TCP Server** (`nomdb-server --port 6379`)
  2. **Embedded Python Library** (`import nomdb; db = nomdb.open_db("app.db")`)
  3. **Self-Hosted Python Server** (`nomdb.serve(port=6379)`)
* 🎨 **Modern Web Management Dashboard**: Inspect keys, edit data, run queries, and monitor live memory usage in real time (`nomdb-dashboard`).
* 🌲 **Custom Native Data Structures**: Strings, Hashes, Lists, Sets, and pure Python **SkipList** with $O(\log N)$ rank/range operations for Sorted Sets.
* ⏳ **Dual Active & Lazy Expiration**: High-precision timestamp min-heap background worker + on-access eviction.
* 💾 **Dual Persistence & Crash Recovery**: AOF (`always`, `everysec`, `no`) with rewriting + Binary Snapshotting (RDB) with SHA-256 integrity checks.
* 🔒 **Transactions & Optimistic Concurrency**: `MULTI`, `EXEC`, `DISCARD`, and versioned `WATCH`/`UNWATCH`.
* 📡 **Pub/Sub & Replication**: Channel and pattern broadcasting, circular replication ring buffer, and `PSYNC` partial resynchronization.
* 🔗 **16,384 CRC16 Cluster Routing**: Hash slot allocation, `{hash_tag}` colocation, and `-MOVED` redirection.

---

## 📥 Installation

Install NomDB via `pip`:

```bash
pip install nomdb
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/TypeAbdullah/NomDB.git
```

Or clone and install locally for development:

```bash
git clone https://github.com/TypeAbdullah/NomDB.git
cd NomDB
pip install -e .
```

---

## 🚀 Quickstart Guides

### 1. Embedded Mode (Zero Server Setup, Stored in Local File)

Use NomDB like SQLite — just import and store in any local file:

```python
import nomdb

# Open local database file (automatically creates data.db)
db = nomdb.open_db("data.db")

# Strings & Numbers
db.set("user:101", "Noman")
print(db.get_str("user:101"))  # "Noman"

db.incr("page_views", 1)       # 1

# Hashes (Objects / Key-Value Mappings)
db.hset("user:101:profile", mapping={"name": "Noman", "role": "Architect"})
print(db.hgetall("user:101:profile"))

# Lists (Queues & Feeds)
db.rpush("tasks", "send_email", "generate_report")
print(db.lrange("tasks", 0, -1))

# Sets (Unique Tags)
db.sadd("tags", "python", "database", "fast")
print(db.smembers("tags"))

# Sorted Sets (Leaderboards backed by SkipList)
db.zadd("leaderboard", {"player_1": 1500.0, "player_2": 2400.0})
print(db.zrange("leaderboard", 0, -1, with_scores=True))

# Close & save snapshot
db.close()
```

---

### 2. Host as a Dedicated TCP Server

#### Option A: Run from Command Line
```bash
nomdb-server --host 127.0.0.1 --port 6379 --data-dir ./data
```

#### Option B: Host Programmatically in Python
```python
import nomdb

# Host directly in your python backend / microservice
nomdb.serve(host="0.0.0.0", port=6379, data_dir="./data")
```

#### Option C: Host in Background Thread (Inside existing Python App)
```python
import nomdb

# Runs the database server in a background daemon thread
server = nomdb.serve_background(port=6379)

# Now your application can connect to it!
client = nomdb.connect("nomdb://127.0.0.1:6379/0")
client.set("hello", "world")
```

---

### 3. Connect via Database URLs

NomDB provides standard database URL formatting:

```python
import nomdb

# Connect to TCP server
client = nomdb.connect("nomdb://:secret@127.0.0.1:6379/0")
client.set("key", "value")

# Connect to embedded local database
db = nomdb.connect("nomdb://./app.db")
db.set("key", "value")
```

---

### 4. Interactive CLI

Launch the interactive REPL with color highlighting:

```bash
nomdb-cli --host 127.0.0.1 --port 6379
```

```text
127.0.0.1:6379> SET user:100 "Noman"
OK
127.0.0.1:6379> GET user:100
"Noman"
127.0.0.1:6379> HSET profile:100 age 28 role "Staff Engineer"
(integer) 2
127.0.0.1:6379> HGETALL profile:100
1) "age"
2) "28"
3) "role"
4) "Staff Engineer"
```

---

## 🌐 Web Management Dashboard

NomDB includes a built-in UI for inspecting and managing database keys:

```bash
nomdb-dashboard --port 8080 --db-port 6379
```

Open **`http://localhost:8080`** in your browser:
* 🔍 **Keyspace Explorer**: Search keys, filter by type (String, Hash, List, Set, ZSet), inspect TTL and memory size.
* 📝 **Data Editor**: View and update values, tabular JSON/Hash viewers, list index inspector, and sorted set member scores.
* ⚡ **Live Performance Monitor**: Real-time memory footprint, ops/sec throughput counter, and total keys.
* 💻 **Interactive Query Console**: Execute any NomDB/Redis command directly in the browser.

---

## 📊 Performance & Stress Test Benchmark

Results from writing **55,000+ entries** across Strings, Hashes, Lists, Sets, and Sorted Sets (`scripts/stress_test_large_data.py`):

| Metric | Measured Value | Threshold Target | Status |
| :--- | :--- | :--- | :--- |
| **Write Throughput** | **250,471 ops/sec** | > 10,000 ops/sec | 🟢 PASS |
| **Write Latency (p50)** | **0.0019 ms** (1.9 µs) | < 20 ms | 🟢 PASS |
| **Write Latency (p99)** | **0.0069 ms** (6.9 µs) | < 20 ms | 🟢 PASS |
| **Read Throughput** | **537,828 ops/sec** | > 50,000 ops/sec | 🟢 PASS |
| **Read Latency (p50)** | **0.0011 ms** (1.1 µs) | < 20 ms | 🟢 PASS |
| **Read Latency (p99)** | **0.0053 ms** (5.3 µs) | < 20 ms | 🟢 PASS |

---

## 🗂 Data Structures & Time Complexity

| Command | Data Structure | Time Complexity | Implementation Details |
| :--- | :--- | :--- | :--- |
| `GET` / `SET` | String | $O(1)$ | Direct keyspace dictionary lookup |
| `INCR` / `DECR` | String | $O(1)$ | Fast in-place integer arithmetic |
| `HGET` / `HSET` | Hash | $O(1)$ | Hash table field lookup/insertion |
| `HGETALL` | Hash | $O(N)$ | Field iteration where $N$ is total fields |
| `LPUSH` / `RPUSH` | List | $O(1)$ | Head/Tail insertion on `collections.deque` |
| `LPOP` / `RPOP` | List | $O(1)$ | Head/Tail pop on `collections.deque` |
| `SADD` / `SREM` | Set | $O(1)$ | Native hash set insertion and deletion |
| `SISMEMBER` | Set | $O(1)$ | Hash set member presence check |
| `ZADD` | Sorted Set | $O(\log N)$ | Custom SkipList level link updates |
| `ZRANK` / `ZREVRANK` | Sorted Set | $O(\log N)$ | SkipList traversal using span pointers |
| `ZSCORE` | Sorted Set | $O(1)$ | Direct lookup via secondary hash table |

---

## 🧪 Running the Test Suite

NomDB has an extensive test suite covering unit tests, end-to-end integration, persistence recovery, replication, cluster hash slots, and protocol fuzzing:

```bash
python -m pytest -v
```

```text
============================= 56 passed in 1.77s ==============================
```

---

## 🐳 Docker Deployment

Run NomDB server in Docker:

```bash
docker build -t nomdb .
docker run -p 6379:6379 -v $(pwd)/data:/app/data nomdb
```

Or spin up a Primary + Replica setup using Docker Compose:

```bash
docker compose up --build
```

---

## 📜 License

NomDB is open source software released under the [MIT License](LICENSE).
