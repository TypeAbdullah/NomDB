# NomDB Complexity & Performance Analysis

---

## 1. Algorithmic Time Complexity Table

| Command | Data Structure | Time Complexity | Notes |
| :--- | :--- | :--- | :--- |
| `GET` | String | $O(1)$ | Direct keyspace dictionary lookup |
| `SET` | String | $O(1)$ | Direct dictionary insertion |
| `DEL` | Any | $O(N)$ | $N$ is the number of keys being deleted |
| `INCR` / `DECR` | String | $O(1)$ | In-place integer arithmetic |
| `HGET` / `HSET` | Hash | $O(1)$ | Dictionary lookup/insert inside hash object |
| `HGETALL` | Hash | $O(N)$ | $N$ is the total field count |
| `LPUSH` / `RPUSH` | List | $O(1)$ | Head/Tail insertion on `collections.deque` |
| `LPOP` / `RPOP` | List | $O(1)$ | Head/Tail pop on `collections.deque` |
| `LRANGE` | List | $O(S + N)$ | $S$ is start offset, $N$ is slice length |
| `SADD` / `SREM` | Set | $O(1)$ | Python set add/remove |
| `SISMEMBER` | Set | $O(1)$ | Set membership test |
| `SUNION` / `SINTER` | Set | $O(N)$ | Set intersection/union |
| `ZADD` | Sorted Set | $O(\log N)$ | SkipList insertion with logarithmic level link update |
| `ZREM` | Sorted Set | $O(\log N)$ | SkipList deletion + dict cleanup |
| `ZSCORE` | Sorted Set | $O(1)$ | Direct lookup via secondary hash table |
| `ZRANK` / `ZREVRANK` | Sorted Set | $O(\log N)$ | SkipList traversal using span pointers |
| `ZRANGE` | Sorted Set | $O(\log N + M)$ | $O(\log N)$ to find start node by rank, $O(M)$ to traverse |

---

## 2. Optimization Insights

1. **Pipelining**:
   * Batching commands reduces TCP network round trips and kernel socket buffer context switches.
   * Benchmarks show up to **25,000+ ops/sec** on single-core Python event loops when pipelining requests.

2. **SkipList with Span Metric**:
   * Pure Python SkipList implementation with span tracking avoids linear $O(N)$ array slicing and expensive sorting on every read.

3. **Active Expiration Priority Queue**:
   * Using a min-heap indexed by timestamp avoids creating per-key asyncio timers or scanning the entire keyspace.
