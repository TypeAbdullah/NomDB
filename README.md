# NomDB ⚡

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-54%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **NomDB** is a production-grade in-memory key-value database built **from scratch in Python using asyncio**.
> It works as both a **standalone TCP database server (RESP protocol)**, an **embedded in-memory database library (`import nomdb`)**, and includes a **web dashboard** for data management.

---

## 🗄 Where Is Data Stored?

| Mode | Snapshot (RDB) File | Append-Only Log (AOF) | Custom Path |
| :--- | :--- | :--- | :--- |
| **Server Mode** | `./data/dump.nomdb` | `./data/appendonly.aof` | `--data-dir ./my_data` |
| **Embedded Mode** | `./nomdb.dump` (or your chosen path) | N/A (Atomic Snapshots) | `nomdb.open_db("./mydb.nomdb")` |

---

## 🚀 1. Embedded Python Usage (Zero Setup, Just Import)

You can use NomDB directly in any Python application with persistent local storage:

```python
import nomdb

# Open local database (creates ./app_data.nomdb automatically)
db = nomdb.open_db("./app_data.nomdb")

# Strings & Numbers
db.set("user:1000", "Noman")
print(db.get_str("user:1000"))  # "Noman"

db.incr("page_views", 1)
print(db.get_str("page_views"))  # "1"

# Hashes (Objects/Dictionaries)
db.hset("session:abc", mapping={"user_id": "1000", "role": "admin"})
print(db.hgetall("session:abc"))  # {"user_id": "1000", "role": "admin"}

# Lists (Queues / Feeds)
db.rpush("task_queue", "email_1", "email_2")
print(db.lrange("task_queue", 0, -1))  # ["email_1", "email_2"]

# Sets (Unique Tags)
db.sadd("user:1000:tags", "python", "database", "ai")
print(db.smembers("user:1000:tags"))  # ["python", "database", "ai"]

# Sorted Sets (Leaderboards with O(log N) SkipList)
db.zadd("leaderboard", {"player_1": 1500.0, "player_2": 2400.0})
print(db.zrange("leaderboard", 0, -1, with_scores=True))

# Save & close
db.close()
```

---

## 🖥 2. Standalone TCP Server & CLI

### Start Database Server
```bash
nomdb-server --host 127.0.0.1 --port 6379
```

### Connect via Interactive CLI
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
```

---

## 🌐 3. Web Dashboard

NomDB includes a built-in web management interface (similar to Supabase / RedisInsight):

```bash
nomdb-dashboard --port 8080 --db-port 6379
```

Open **`http://localhost:8080`** in your browser:
* **Interactive Keyspace Explorer**: Live search, filter by type (String, Hash, List, Set, ZSet), view TTL and size.
* **Data Inspector**: View values, tabular field viewers, list indexes, and sorted set member scores.
* **Create / Edit / Delete**: Add new keys with custom TTL, edit values, or delete records.
* **Real-time Server Metrics**: Track used memory, ops/sec, total keys, and uptime.
* **Built-in Console / Query Runner**: Execute raw commands directly from the dashboard.

---

## ⚡ 4. Latency & Performance Verification

NomDB executes operations with sub-millisecond latencies (well under the 20 ms threshold):

### Large Data Stress Test (55,000+ Entries)

```powershell
python scripts/stress_test_large_data.py
```

```text
=================================================================
                    LATENCY & THROUGHPUT REPORT                 
=================================================================
Total Entries Created:     55,151
Snapshot File Size:        4.65 MB
Snapshot Save Time:        136.44 ms
-----------------------------------------------------------------
WRITE Speed:               250,471 ops/sec
  - Average Latency:       0.0026 ms
  - p50 Latency:           0.0019 ms  (< 20 ms -> PASS)
  - p95 Latency:           0.0039 ms  (< 20 ms -> PASS)
  - p99 Latency:           0.0069 ms  (< 20 ms -> PASS)
-----------------------------------------------------------------
READ Speed:                537,828 ops/sec
  - Average Latency:       0.0014 ms
  - p50 Latency:           0.0011 ms  (< 20 ms -> PASS)
  - p95 Latency:           0.0026 ms  (< 20 ms -> PASS)
  - p99 Latency:           0.0053 ms  (< 20 ms -> PASS)
=================================================================
```

---

## 🧪 5. Testing

Run all 54 unit, integration, replication, persistence, cluster, and fuzz tests:

```bash
pytest -v
```
