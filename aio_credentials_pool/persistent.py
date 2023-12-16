import asyncio
import logging
import sys
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from models import Credential
from settings import POSTGRES_URL
from sqlalchemy import nullsfirst, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# Create a formatter with a timestamp
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Create a handler for console output (stdout) with the defined formatter
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
LOGGER.addHandler(console_handler)

engine = create_async_engine(POSTGRES_URL)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


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


class PersistentCredentialsPool:
    async def acquire(self):
        async with get_session() as session:
            credential = (
                await session.execute(
                    select(Credential)
                    .filter(Credential.in_use == False)
                    .order_by(nullsfirst(Credential.date_last_usage.asc()))
                    .with_for_update(skip_locked=True),
                )
            ).scalar()
            if not credential:
                raise Exception('No available credentials')

            credential.date_last_usage = datetime.now()
            credential.in_use = True
            return credential

    async def release(self, credential: Credential):
        async with get_session() as session:
            db_credential = await session.get(Credential, credential.id)
            if db_credential:
                db_credential.in_use = False
            else:
                raise ValueError('Credential not found in the database')

async def worker(pool, worker_id: int):
    while True:
        try:
            credential = await pool.acquire()
            if credential:
                LOGGER.info(f'Worker {worker_id} acquired credentials: {credential}')
                await asyncio.sleep(random.randint(1, 5))
                await pool.release(credential)
                LOGGER.info(f'Worker {worker_id} released credentials: {credential}')
        except Exception as e:
            LOGGER.info(f'Worker {worker_id} encountered an error: {e}')
        await asyncio.sleep(random.randint(1, 5))


async def main():
    pool = PersistentCredentialsPool()

    num_workers = 100

    worker_tasks = []

    for i in range(num_workers):
        worker_tasks.append(asyncio.create_task(worker(pool, i)))

    await asyncio.gather(*worker_tasks)


if __name__ == '__main__':
    asyncio.run(main())
