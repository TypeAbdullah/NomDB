# NomDB Cluster & Hash Slots

NomDB supports distributed clustering based on **16,384 CRC16 Hash Slots** with hash tag extraction and client routing.

---

## 1. Slot Allocation & Hash Algorithm

* **Total Slots**: 16,384 (numbered `0` to `16383`).
* **Hash Formula**:
  $$\text{slot} = \text{CRC16}(\text{hash\_tag}(\text{key})) \pmod{16384}$$

### Hash Tags
If a key contains `{...}` and the enclosed text is non-empty, only the text inside the first pair of braces is hashed:
* `user:{1000}:profile` $\rightarrow$ hashes `1000` $\rightarrow$ Slot `1234`
* `user:{1000}:orders` $\rightarrow$ hashes `1000` $\rightarrow$ Slot `1234`

This guarantees that related keys hash to the same node, enabling atomic multi-key commands (`MGET`, `MSET`, transactions) across those keys.

---

## 2. Redirection Protocol

When a client queries a node for a key that maps to a slot owned by a different node:
* The server responds with:
  ```text
  -MOVED <slot> <node_ip>:<node_port>\r\n
  ```
* The client refreshes its cluster slot cache and redirects the query to the correct target node.
