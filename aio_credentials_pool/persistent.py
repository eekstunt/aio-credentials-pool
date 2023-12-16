import asyncio
import logging
import random
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from models import Credential
from settings import POSTGRES_URL
from sqlalchemy import nullsfirst, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
LOGGER.addHandler(console_handler)

engine = create_async_engine(POSTGRES_URL)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

stop_event = asyncio.Event()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class NoAvailableCredentials(Exception):
    pass


class PersistentCredentialsPool:
    async def acquire(self, max_retries=3, min_wait=1, max_wait=32):
        current_wait = min_wait

        for attempt in range(max_retries):
            async with get_session() as session:
                credential = (
                    await session.execute(
                        select(Credential)
                        .filter(Credential.in_use == False)
                        .order_by(nullsfirst(Credential.date_last_usage.asc()))
                        .limit(1)
                        .with_for_update(skip_locked=True),
                    )
                ).scalar()

                if credential:
                    credential.date_last_usage = datetime.now()
                    credential.in_use = True
                    return credential

            await asyncio.sleep(min(current_wait, max_wait))
            current_wait *= 2

        raise NoAvailableCredentials('No available credentials after retries')

    async def release(self, credential: Credential):
        async with get_session() as session:
            db_credential = await session.get(Credential, credential.id)
            if db_credential:
                db_credential.in_use = False
            else:
                raise ValueError('Credential not found in the database')


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


async def main():
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: loop.create_task(shutdown(s)))

    pool = PersistentCredentialsPool()

    num_workers = 2000

    worker_tasks = []

    for i in range(num_workers):
        worker_tasks.append(loop.create_task(worker(pool, i)))

    await asyncio.gather(*worker_tasks)


if __name__ == '__main__':
    asyncio.run(main())
