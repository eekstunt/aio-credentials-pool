import asyncio

import pytest
from base_credentials_pool import NoAvailableCredentialsError
from in_memory_credentials_pool import (
    CredentialMetadata,
    InMemoryCredentialsPool,
)


@pytest.fixture()
def credentials():
    return [
        CredentialMetadata('user1', 'pass1', 'cookie1'),
        CredentialMetadata('user2', 'pass2', 'cookie2'),
        CredentialMetadata('user3', 'pass3', 'cookie3'),
    ]


@pytest.mark.asyncio()
async def test_race_condition(credentials):
    async def acquire_and_release(pool: InMemoryCredentialsPool, acquired_credential: CredentialMetadata):
        credential = None
        try:
            credential = await pool.acquire(max_retries=0)
            assert credential.username != acquired_credential.username
            await asyncio.sleep(0.02)
        except NoAvailableCredentialsError:
            pass
        finally:
            if credential:
                await pool.release(credential)

    credentials_pool = InMemoryCredentialsPool(credentials)
    acquired_credential = await credentials_pool.acquire()
    tasks = [acquire_and_release(credentials_pool, acquired_credential) for _ in range(10)]

    await asyncio.gather(*tasks)


@pytest.mark.asyncio()
async def test_no_available_credentials(credentials):
    async def acquire_and_release(pool: InMemoryCredentialsPool):
        credential = await pool.acquire(max_retries=0)
        await asyncio.sleep(0.3)
        await pool.release(credential)

    credentials_pool = InMemoryCredentialsPool(credentials)
    tasks = [acquire_and_release(credentials_pool) for _ in range(7)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    no_available_count = sum(isinstance(result, NoAvailableCredentialsError) for result in results)

    assert no_available_count >= 1, 'Expected one or more NoAvailableCredentialsError exceptions'
