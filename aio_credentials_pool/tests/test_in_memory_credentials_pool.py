import asyncio
import pytest
from in_memory_credentials_pool import (
    CredentialsPool,
    Credential,
    NoCredentialError,
    get_credential,
)


@pytest.fixture
def credentials():
    return [
        Credential("user1", "pass1", "cookie1"),
        Credential("user2", "pass2", "cookie2"),
        Credential("user3", "pass3", "cookie3"),
    ]


@pytest.mark.asyncio
async def test_race_condition(credentials):
    async def acquire_and_release(
        pool: CredentialsPool, acquired_credential: Credential
    ):
        async with get_credential(pool, timeout=10) as credential:
            assert credential.username != acquired_credential.username
            await asyncio.sleep(0.02)

    credentials_pool = CredentialsPool(credentials)
    acquired_credential = await credentials_pool.acquire()
    tasks = [
        acquire_and_release(credentials_pool, acquired_credential) for _ in range(10)
    ]

    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_acquiring_timeout(credentials):
    async def acquire_and_release(pool: CredentialsPool):
        try:
            async with get_credential(pool, timeout=0.2):
                await asyncio.sleep(0.3)
        except NoCredentialError:
            return "Timeout occurred"

    credentials_pool = CredentialsPool(credentials)
    tasks = [acquire_and_release(credentials_pool) for _ in range(5)]

    results = await asyncio.gather(*tasks)

    assert "Timeout occurred" in results
