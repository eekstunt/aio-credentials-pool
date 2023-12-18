import asyncio

from base_credentials_pool import BaseCredentialsPool, CredentialMetadata


class InMemoryCredentialsPool(BaseCredentialsPool):
    def __init__(self, credentials: list[CredentialMetadata]):
        self.credentials = credentials
        self.lock = asyncio.Lock()

    async def _acquire(self) -> CredentialMetadata | None:
        async with self.lock:
            if self.credentials:
                return self.credentials.pop(0)
        return None

    async def _release(self, credential: CredentialMetadata) -> None:
        async with self.lock:
            self.credentials.append(credential)
