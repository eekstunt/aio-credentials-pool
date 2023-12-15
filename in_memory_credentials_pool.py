import asyncio
import json
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class Credential:
    username: str
    password: str
    cookie: str | None


class NoCredentialError(Exception):
    pass


class CredentialsPool:
    def __init__(self, credentials: list[Credential]):
        self.credentials = credentials
        self.lock = asyncio.Lock()

    async def acquire(self, timeout=10):
        start_time = asyncio.get_event_loop().time()
        while True:
            async with self.lock:
                if self.credentials:
                    return self.credentials.pop(0)
            if asyncio.get_event_loop().time() - start_time > timeout:
                break
            await asyncio.sleep(0.1)
        raise NoCredentialError()

    async def release(self, credential):
        async with self.lock:
            self.credentials.append(credential)


@asynccontextmanager
async def get_credential(pool: CredentialsPool, timeout=10):
    credential = await pool.acquire(timeout)
    try:
        print(f"Acquired credential: {credential.username}")
        yield credential
    finally:
        await pool.release(credential)
        print(f"Released credential: {credential.username}")


async def access_credential(pool: CredentialsPool) -> None:
    async with get_credential(pool):
        await asyncio.sleep(4)


async def main():
    with open("credentials.json") as f:
        credentials = [
            Credential(
                username=c["username"], password=c["password"], cookie=c["cookie"]
            )
            for c in json.load(f)
        ]

    pool = CredentialsPool(credentials)

    num_workers = 1000

    worker_tasks = [access_credential(pool) for _ in range(num_workers)]

    await asyncio.gather(*worker_tasks)


if __name__ == "__main__":
    asyncio.run(main())
