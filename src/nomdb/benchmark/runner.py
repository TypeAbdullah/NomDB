"""
High-Performance Benchmark Suite for NomDB.
Measures requests/sec, throughput, and latency percentiles (p50, p95, p99) under concurrent load.
"""

from __future__ import annotations
import argparse
import asyncio
import math
import statistics
import time
from typing import List, Tuple
from nomdb.client.pool import AsyncConnection
from nomdb.protocol.encoder import RESPEncoder


async def benchmark_worker(
    host: str,
    port: int,
    command_name: str,
    requests_per_worker: int,
    pipeline_size: int,
    worker_id: int,
) -> List[float]:
    """Single benchmark worker executing pipelined or single requests and recording latencies in ms."""
    latencies: List[float] = []
    conn = AsyncConnection(host, port)
    await conn.connect()

    req_count = 0
    batch_size = max(1, pipeline_size)

    try:
        while req_count < requests_per_worker:
            current_batch = min(batch_size, requests_per_worker - req_count)
            t0 = time.perf_counter()

            # Construct batch
            payloads = []
            for i in range(current_batch):
                idx = req_count + i
                key = f"bench:{worker_id}:{idx}".encode("ascii")
                val = b"val_" + str(idx).encode("ascii")

                if command_name == "SET":
                    payloads.append(RESPEncoder.encode_command(b"SET", key, val))
                elif command_name == "GET":
                    payloads.append(RESPEncoder.encode_command(b"GET", key))
                elif command_name == "INCR":
                    payloads.append(RESPEncoder.encode_command(b"INCR", b"counter_" + str(worker_id).encode("ascii")))
                elif command_name == "LPUSH":
                    payloads.append(RESPEncoder.encode_command(b"LPUSH", b"list_" + str(worker_id).encode("ascii"), val))
                elif command_name == "HSET":
                    payloads.append(RESPEncoder.encode_command(b"HSET", b"hash_" + str(worker_id).encode("ascii"), key, val))
                elif command_name == "SADD":
                    payloads.append(RESPEncoder.encode_command(b"SADD", b"set_" + str(worker_id).encode("ascii"), val))
                elif command_name == "PING":
                    payloads.append(RESPEncoder.encode_command(b"PING"))
                else:
                    payloads.append(RESPEncoder.encode_command(b"PING"))

            # Send burst
            conn.writer.write(b"".join(payloads))
            await conn.writer.drain()

            # Read responses
            received = 0
            # Drain any already buffered commands
            buffered = conn.parser.get_parsed_commands()
            received += len(buffered)

            while received < current_batch:
                chunk = await conn.reader.read(65536)
                if not chunk:
                    break
                conn.parser.feed(chunk)
                cmds = conn.parser.get_parsed_commands()
                received += len(cmds)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            # Record latency per request in batch
            avg_per_req = elapsed_ms / current_batch
            for _ in range(current_batch):
                latencies.append(avg_per_req)

            req_count += current_batch

    finally:
        await conn.close()

    return latencies


async def run_benchmark_for_command(
    host: str,
    port: int,
    command_name: str,
    total_requests: int,
    concurrency: int,
    pipeline_size: int,
) -> None:
    """Run concurrent benchmark for a single command type."""
    print(f"\n====== {command_name.upper()} ======")
    req_per_worker = total_requests // concurrency

    t_start = time.perf_counter()
    tasks = [
        benchmark_worker(host, port, command_name.upper(), req_per_worker, pipeline_size, worker_id)
        for worker_id in range(concurrency)
    ]
    results = await asyncio.gather(*tasks)
    total_time_sec = time.perf_counter() - t_start

    all_latencies = []
    for r in results:
        all_latencies.extend(r)

    if not all_latencies:
        print("No latency samples collected.")
        return

    all_latencies.sort()
    n = len(all_latencies)
    throughput = n / total_time_sec

    avg_lat = statistics.mean(all_latencies)
    p50 = all_latencies[int(n * 0.50)]
    p95 = all_latencies[int(n * 0.95)]
    p99 = all_latencies[int(n * 0.99)]
    min_lat = all_latencies[0]
    max_lat = all_latencies[-1]

    print(f"  Requests completed:  {n:,}")
    print(f"  Concurrency:         {concurrency} clients")
    print(f"  Pipeline:            {pipeline_size}")
    print(f"  Total Duration:      {total_time_sec:.3f} s")
    print(f"  Throughput:          \033[92m{throughput:,.2f} ops/sec\033[0m")
    print(f"  Latency (avg):       {avg_lat:.2f} ms")
    print(f"  Latency (p50):       {p50:.2f} ms")
    print(f"  Latency (p95):       {p95:.2f} ms")
    print(f"  Latency (p99):       {p99:.2f} ms")
    print(f"  Latency (min/max):   {min_lat:.2f} ms / {max_lat:.2f} ms")


async def main_async(args: argparse.Namespace) -> None:
    tests = [t.strip().upper() for t in args.tests.split(",")]
    print(f"Starting NomDB Benchmark against {args.host}:{args.port}")
    print(f"Total requests: {args.requests:,}, Concurrency: {args.clients}, Pipeline: {args.pipeline}")

    for cmd in tests:
        await run_benchmark_for_command(
            args.host,
            args.port,
            cmd,
            args.requests,
            args.clients,
            args.pipeline,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="NomDB Benchmark Tool")
    parser.add_argument("-h", "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("-p", "--port", type=int, default=6379, help="Server port (default: 6379)")
    parser.add_argument("-c", "--clients", type=int, default=20, help="Number of parallel clients (default: 20)")
    parser.add_argument("-n", "--requests", type=int, default=10000, help="Total number of requests (default: 10000)")
    parser.add_argument("-P", "--pipeline", type=int, default=1, help="Pipeline requests in batch (default: 1)")
    parser.add_argument("-t", "--tests", default="PING,SET,GET,INCR,LPUSH,HSET", help="Comma-separated test list")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
