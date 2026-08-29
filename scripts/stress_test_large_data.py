import os
import statistics
import time
from pathlib import Path
import nomdb

def run_large_data_stress_test(total_keys: int = 50000):
    print("=" * 65)
    print(f"        NOMDB LARGE DATA STRESS & LATENCY TEST ({total_keys:,} KEYS)       ")
    print("=" * 65)

    db_path = Path("./stress_test_db.nomdb")
    if db_path.exists():
        db_path.unlink()

    # 1. Initialize embedded NomDB
    db = nomdb.open_db(path=db_path, auto_save=False)

    print(f"\n[1/4] Writing {total_keys:,} keys into memory...")
    write_latencies = []
    t_start_write = time.perf_counter()

    for i in range(total_keys):
        key = f"user:account:{i}"
        val = f"account_payload_data_hash_{i}_timestamp_{time.time()}"
        t0 = time.perf_counter()
        db.set(key, val)
        write_lat = (time.perf_counter() - t0) * 1000.0
        write_latencies.append(write_lat)

    total_write_time = time.perf_counter() - t_start_write
    write_ops = total_keys / total_write_time

    # 2. Add Hashes, Lists, Sets, ZSets
    print("[2/4] Writing complex data structures (Hashes, Lists, Sets, ZSets)...")
    for i in range(5000):
        db.hset(f"profile:{i}", mapping={"name": f"User_{i}", "age": str(20 + i % 50), "city": "NYC"})
        db.rpush(f"queue:{i % 100}", f"job_{i}")
        db.sadd(f"tags:{i % 50}", f"tag_{i % 200}")
        db.zadd("global_leaderboard", {f"player_{i}": float(i * 1.5)})

    # 3. Read Latency Test
    print(f"[3/4] Performing {total_keys:,} random key reads...")
    read_latencies = []
    t_start_read = time.perf_counter()

    for i in range(total_keys):
        key = f"user:account:{i}"
        t0 = time.perf_counter()
        val = db.get(key)
        read_lat = (time.perf_counter() - t0) * 1000.0
        read_latencies.append(read_lat)
        assert val is not None

    total_read_time = time.perf_counter() - t_start_read
    read_ops = total_keys / total_read_time

    # 4. Persistence Save Test
    print(f"[4/4] Saving snapshot to disk ({db_path.name})...")
    t_save_start = time.perf_counter()
    db.save()
    save_duration = (time.perf_counter() - t_save_start) * 1000.0
    file_size_mb = db_path.stat().st_size / (1024 * 1024)

    # Compute Statistics
    write_latencies.sort()
    read_latencies.sort()

    w_avg = statistics.mean(write_latencies)
    w_p50 = write_latencies[int(len(write_latencies) * 0.50)]
    w_p95 = write_latencies[int(len(write_latencies) * 0.95)]
    w_p99 = write_latencies[int(len(write_latencies) * 0.99)]
    w_max = write_latencies[-1]

    r_avg = statistics.mean(read_latencies)
    r_p50 = read_latencies[int(len(read_latencies) * 0.50)]
    r_p95 = read_latencies[int(len(read_latencies) * 0.95)]
    r_p99 = read_latencies[int(len(read_latencies) * 0.99)]
    r_max = read_latencies[-1]

    print("\n" + "=" * 65)
    print("                    LATENCY & THROUGHPUT REPORT                 ")
    print("=" * 65)
    print(f"Total Entries Created:     {db.dbsize():,}")
    print(f"Snapshot File Size:        {file_size_mb:.2f} MB")
    print(f"Snapshot Save Time:        {save_duration:.2f} ms")
    print("-" * 65)
    print(f"WRITE Speed:               {write_ops:,.2f} ops/sec")
    print(f"  - Average Latency:       {w_avg:.4f} ms")
    print(f"  - p50 Latency:           {w_p50:.4f} ms  (Target: < 20 ms) -> {'PASS' if w_p50 < 20 else 'FAIL'}")
    print(f"  - p95 Latency:           {w_p95:.4f} ms  (Target: < 20 ms) -> {'PASS' if w_p95 < 20 else 'FAIL'}")
    print(f"  - p99 Latency:           {w_p99:.4f} ms  (Target: < 20 ms) -> {'PASS' if w_p99 < 20 else 'FAIL'}")
    print(f"  - Max Latency:           {w_max:.4f} ms")
    print("-" * 65)
    print(f"READ Speed:                {read_ops:,.2f} ops/sec")
    print(f"  - Average Latency:       {r_avg:.4f} ms")
    print(f"  - p50 Latency:           {r_p50:.4f} ms  (Target: < 20 ms) -> {'PASS' if r_p50 < 20 else 'FAIL'}")
    print(f"  - p95 Latency:           {r_p95:.4f} ms  (Target: < 20 ms) -> {'PASS' if r_p95 < 20 else 'FAIL'}")
    print(f"  - p99 Latency:           {r_p99:.4f} ms  (Target: < 20 ms) -> {'PASS' if r_p99 < 20 else 'FAIL'}")
    print(f"  - Max Latency:           {r_max:.4f} ms")
    print("=" * 65)

    # Clean up test artifact
    if db_path.exists():
        db_path.unlink()

if __name__ == "__main__":
    run_large_data_stress_test(50000)
