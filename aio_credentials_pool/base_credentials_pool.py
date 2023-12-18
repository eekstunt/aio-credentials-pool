import asyncio
import logging
from dataclasses import dataclass

from models import Credential

LOGGER = logging.getLogger(__name__)


class NoAvailableCredentialsError(Exception):
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

        for attempt in range(max_retries + 1):
            credential = await self._acquire()

            if credential:
                LOGGER.info(f'Credential acquired: {credential}')
                return credential

            if attempt < max_retries:
                wait_seconds = min(current_wait, max_wait)
                LOGGER.info(f'Failed to acquire credential. Will retry in {wait_seconds} seconds')
                await asyncio.sleep(wait_seconds)
                current_wait *= 2

        raise NoAvailableCredentialsError(f'No available credentials after {max_retries} retries')

    async def release(self, credential: CredentialMetadata) -> None:
        await self._release(credential)
        LOGGER.info(f'Credential released: {credential}')

    async def _acquire(self) -> CredentialMetadata | None:
        raise NotImplementedError

    async def _release(self, credential: CredentialMetadata) -> None:
        raise NotImplementedError
