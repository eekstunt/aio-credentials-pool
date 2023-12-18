from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from base_credentials_pool import BaseCredentialsPool, CredentialMetadata
from models import Credential
from settings import POSTGRES_URL
from sqlalchemy import nullsfirst, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


class PersistentCredentialsPool(BaseCredentialsPool):
    async def _acquire(self) -> CredentialMetadata | None:
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
                return CredentialMetadata.from_orm(credential)

        return None

    async def _release(self, credential: Credential):
        async with get_session() as session:
            db_credential = (await session.execute(select(Credential).filter_by(username=credential.username))).scalar()
            if db_credential:
                db_credential.in_use = False
            else:
                raise ValueError('Credential not found in the database')
