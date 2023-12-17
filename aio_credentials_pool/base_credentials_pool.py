import asyncio
from dataclasses import dataclass

from models import Credential


class NoAvailableCredentials(Exception):
    pass


@dataclass
class CredentialMetadata:
    username: str
    password: str
    cookie: str | None

    @classmethod
    def from_orm(cls, credential: Credential) -> 'CredentialMetadata':
        return cls(
            username=credential.username,
            password=credential.password,
            cookie=credential.cookie,
        )


class BaseCredentialsPool:
    async def acquire(self, max_retries=3, min_wait=1, max_wait=32) -> CredentialMetadata:
        current_wait = min_wait

        for attempt in range(max_retries):
            credential = await self._acquire()

            if credential:
                return credential
            await asyncio.sleep(min(current_wait, max_wait))
            current_wait *= 2

        raise NoAvailableCredentials('No available credentials after retries')

    async def release(self, credential):
        pass

    async def _acquire(self) -> CredentialMetadata | None:
        raise NotImplementedError
