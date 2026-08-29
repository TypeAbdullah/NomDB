# NomDB Protocol Specification (RESP)

NomDB communicates over standard TCP using the **Redis Serialization Protocol (RESP2 / RESP3)**.

---

## 1. RESP Type Formats

| Type | Prefix Byte | Wire Format | Example |
| :--- | :--- | :--- | :--- |
| **Simple String** | `+` | `+<string>\r\n` | `+OK\r\n` |
| **Error** | `-` | `-<error_message>\r\n` | `-ERR unknown command\r\n` |
| **Integer** | `:` | `:<number>\r\n` | `:1000\r\n` |
| **Bulk String** | `$` | `$<length>\r\n<bytes>\r\n` | `$5\r\nhello\r\n` |
| **Null Bulk String**| `$` | `$-1\r\n` | `$-1\r\n` |
| **Array** | `*` | `*<count>\r\n<item_1>...` | `*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n` |
| **Null Array** | `*` | `*-1\r\n` | `*-1\r\n` |

---

## 2. Request & Response Examples

### Ping Command
* Request:
  ```text
  *1\r\n$4\r\nPING\r\n
  ```
* Response:
  ```text
  +PONG\r\n
  ```

### Setting a String with TTL
* Request:
  ```text
  *5\r\n$3\r\nSET\r\n$4\r\nuser\r\n$5\r\nNoman\r\n$2\r\nEX\r\n$2\r\n60\r\n
  ```
* Response:
  ```text
  +OK\r\n
  ```

### Querying Hash Field
* Request:
  ```text
  *3\r\n$4\r\nHGET\r\n$6\r\nuser:1\r\n$4\r\nname\r\n
  ```
* Response:
  ```text
  $5\r\nNoman\r\n
  ```

---

## 3. Streaming Parser & Edge Cases

The NomDB `RESPParser` is built to handle:
1. **Partial / Fragmented TCP Chunks**: If a TCP packet contains only the first half of a bulk string or array header, the parser maintains position and waits for subsequent packets without raising false errors.
2. **Pipelining**: Multiple commands arriving in a single `read()` call are segmented and processed in order.
3. **Inline Commands**: Non-RESP plain text commands (such as `PING\r\n` from netcat / telnet) are parsed and executed correctly.
4. **Fuzz Protection**: Memory size guards prevent allocating buffers beyond `max_buffer_size` when encountering corrupted length headers.
