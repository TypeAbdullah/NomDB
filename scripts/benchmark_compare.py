"""
Benchmark comparison script: NomDB vs Redis (if available).
Runs identical workloads and reports throughput, latency (p50/p95/p99), and memory usage.
"""

import argparse
import asyncio
import time
from nomdb.benchmark.runner import run_benchmark_for_command


async def main():
    parser = argparse.ArgumentParser(description="NomDB vs Redis Benchmark Comparison")
    parser.add_argument("--nomdb-port", type=int, default=6379, help="NomDB port (default: 6379)")
    parser.add_argument("--redis-port", type=int, default=6380, help="Redis port (default: 6380)")
    parser.add_argument("-n", "--requests", type=int, default=10000, help="Total requests per test")
    parser.add_argument("-c", "--clients", type=int, default=20, help="Concurrency")
    parser.add_argument("-P", "--pipeline", type=int, default=16, help="Pipeline batch size")

    args = parser.parse_args()

    print("================================================================")
    print("                    NOMDB BENCHMARK RUNNER                      ")
    print("================================================================")
    print(f"Target: 127.0.0.1:{args.nomdb_port} | Requests: {args.requests:,} | Concurrency: {args.clients} | Pipeline: {args.pipeline}")

    for cmd in ["SET", "GET", "INCR", "LPUSH", "HSET"]:
        try:
            await run_benchmark_for_command("127.0.0.1", args.nomdb_port, cmd, args.requests, args.clients, args.pipeline)
        except Exception as e:
            print(f"NomDB Benchmark for {cmd} error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
