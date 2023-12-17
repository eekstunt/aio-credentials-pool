import asyncio
import logging
import random
import signal
import sys
import argparse

from persistent import PersistentCredentialsPool

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
LOGGER.addHandler(console_handler)


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
        except Exception as e:
            LOGGER.info(f'Worker {worker_id} encountered an error: {e}')
        finally:
            if stop_event.is_set() and credential:
                await pool.release(credential)
        await asyncio.sleep(random.randint(1, 5))


async def shutdown(sig: signal.Signals) -> None:
    LOGGER.info(f'Received exit signal {sig.name}...')
    LOGGER.info('Sending stop event to workers to allow them release all acquired credentials...')
    stop_event.set()


async def main(num_workers: int):
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: loop.create_task(shutdown(s)))

    pool = PersistentCredentialsPool()

    worker_tasks = []

    for i in range(num_workers):
        worker_tasks.append(loop.create_task(worker(pool, i)))

    await asyncio.gather(*worker_tasks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run workers with specified concurrency')
    parser.add_argument('--workers', type=int, default=2000, help='Number of workers')

    args = parser.parse_args()
    asyncio.run(main(args.workers))
