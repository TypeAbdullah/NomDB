# NomDB Persistence & Crash Recovery

NomDB provides two persistent storage engines: **AOF (Append-Only File)** and **Point-in-time Binary Snapshots (RDB)**.

---

## 1. Append-Only File (AOF)

The AOF log logs every mutating write command in pure RESP format.

### Fsync Policies
* **`always`**: `os.fsync()` is executed after every single write command. Provides maximum durability at the cost of disk I/O throughput.
* **`everysec`** (Default): A dedicated asynchronous background worker flushes and fsyncs dirty buffers every 1 second. Guarantees that at most 1 second of writes could be lost during power failure.
* **`no`**: Buffer flushing is handled entirely by the host operating system. Highest throughput.

### AOF Rewriting
To prevent unbounded log growth, `AOFManager.rewrite()` iterates over the active keyspaces and generates the minimal set of RESP commands needed to restore the current memory state to a temporary file before atomically swapping the file.

---

## 2. Binary Snapshot (RDB-style)

Snapshots save a full dump of the database keyspaces in a compact binary format.

### Format Specification
```text
+-----------------------+---------------------+
| Field                 | Size / Type         |
+-----------------------+---------------------+
| Magic Bytes ("NOMDB") | 5 bytes             |
| Version (1)           | 2 bytes (uint16)    |
| DB Selector Opcode    | 1 byte  (0xFE)      |
| DB ID                 | 2 bytes (uint16)    |
| [Optional] Expire Op  | 1 byte  (0xFD)      |
| [Optional] Expire MS  | 8 bytes (uint64)    |
| Data Type Opcode      | 1 byte              |
| Key Length            | 4 bytes (uint32)    |
| Key Bytes             | Variable            |
| Value Length          | 4 bytes (uint32)    |
| Value Bytes           | Variable            |
| EOF Opcode            | 1 byte  (0xFF)      |
| SHA-256 Checksum      | 32 bytes            |
+-----------------------+---------------------+
```

### Snapshot Commands
* **`SAVE`**: Synchronously writes snapshot to disk. Blocks client interactions.
* **`BGSAVE`**: Runs snapshot generation inside an asynchronous thread executor (`run_in_executor`), allowing the event loop to continue serving client queries concurrently.

---

## 3. Crash Recovery

On server boot:
1. If AOF is enabled and exists, the server replays the AOF log from beginning to end.
2. If AOF is disabled and a snapshot file exists, the server validates the SHA-256 checksum and loads all keyspaces.
3. If an AOF log was cut off due to an ungraceful system crash (truncated trailing bytes), the parser recovers all intact commands up to the point of corruption with a logged warning.
4. Active expiration priority heaps are reconstructed immediately after restoration.
