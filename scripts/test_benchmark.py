import asyncio
from nomdb.server.server import NomDBServer
from nomdb.config.settings import ServerSettings
from nomdb.benchmark.runner import benchmark_worker, run_benchmark_for_command

async def main():
    settings = ServerSettings(port=6401, aof_enabled=False, metrics_enabled=False)
    server = NomDBServer(settings)
    await server.start()
    print("Server started on 6401")
    try:
        await run_benchmark_for_command('127.0.0.1', 6401, 'PING', total_requests=1000, concurrency=5, pipeline_size=1)
        await run_benchmark_for_command('127.0.0.1', 6401, 'SET', total_requests=1000, concurrency=5, pipeline_size=16)
        await run_benchmark_for_command('127.0.0.1', 6401, 'GET', total_requests=1000, concurrency=5, pipeline_size=16)
    finally:
        await server.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
