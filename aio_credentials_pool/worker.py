import argparse
import asyncio
import json
import logging
import random
import signal
from pathlib import Path

from base_credentials_pool import BaseCredentialsPool, CredentialMetadata
from in_memory_credentials_pool import InMemoryCredentialsPool
from persistent_credentials_pool import PersistentCredentialsPool

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

stop_event = asyncio.Event()


async def worker(pool, worker_id: int):
    credential = None

    while not stop_event.is_set():
        try:
            credential = await pool.acquire()
            if credential:
                LOGGER.info(f'Worker {worker_id} acquired credentials: {credential}')
                await asyncio.sleep(random.randint(1, 5))
                await pool.release(credential)
                LOGGER.info(f'Worker {worker_id} released credentials: {credential}')
        except Exception:
            LOGGER.exception(f'Worker {worker_id} encountered an error')
        finally:
            if stop_event.is_set() and credential:
                await pool.release(credential)
        await asyncio.sleep(random.randint(1, 5))


async def shutdown(sig: signal.Signals) -> None:
    LOGGER.info(f'Received exit signal {sig.name}...')
    LOGGER.info('Sending stop event to workers to allow them release all acquired credentials...')
    stop_event.set()


async def main(pool: BaseCredentialsPool, num_workers: int) -> None:
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: loop.create_task(shutdown(s)))

    worker_tasks = [loop.create_task(worker(pool, i)) for i in range(num_workers)]

    await asyncio.gather(*worker_tasks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run workers with specified concurrency')
    parser.add_argument('--workers', type=int, default=2000, help='Number of workers')
    parser.add_argument(
        '--pool_type',
        choices=['in_memory', 'persistent'],
        default='persistent',
        help='Type of credentials pool',
    )

    args = parser.parse_args()

    if args.pool_type == 'in_memory':
        credentials_file = Path('fixtures/credentials.json')

        with credentials_file.open() as f:
            credentials = [
                CredentialMetadata(username=c['username'], password=c['password'], cookie=c['cookie'])
                for c in json.load(f)
            ]
        pool = InMemoryCredentialsPool(credentials[:1])
    else:
        pool = PersistentCredentialsPool()

    asyncio.run(main(pool, args.workers))
