import asyncio

import asyncpg
import pytest
import pytest_asyncio
from base_credentials_pool import CredentialMetadata, NoAvailableCredentialsError
from models import Base, Credential
from persistent_credentials_pool import PersistentCredentialsPool, NoCredentialsAtDatabaseError, CredentialNotFoundError
from settings import POSTGRES_URL
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def engine(database_name):
    url = make_url(POSTGRES_URL)
    connection = await asyncpg.connect(user=url.username, password=url.password, host=url.host)

    try:
        databases = await connection.fetch(f"SELECT datname FROM pg_database WHERE datname='{database_name}'")
        if not any(database_name in db.values() for db in databases):
            await connection.execute(f'CREATE DATABASE {database_name}')
            print(f'Database {database_name} created successfully.')
    finally:
        await connection.close()

    test_engine = create_async_engine(
        make_url(POSTGRES_URL).set(database=database_name),
    )
    yield test_engine


@pytest_asyncio.fixture()
async def schema_manager(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope='function')
async def session(engine, schema_manager, mocker):
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    mocker.patch('persistent_credentials_pool.async_session', async_session)

    yield async_session


@pytest.mark.asyncio()
async def test_acquiring_single_credential_by_multiple_workers(session):
    single_credential = Credential(username='test_user3', password='pass1', in_use=False)

    async with session() as _session:
        _session.add(single_credential)
        await _session.commit()

    credentials_pool = PersistentCredentialsPool()

    num_workers = 10
    tasks = [credentials_pool.acquire(max_retries=0) for _ in range(num_workers)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    no_available_count = 0
    acquired_credentials = []
    for result in results:
        if isinstance(result, NoAvailableCredentialsError):
            no_available_count += 1
        else:
            acquired_credentials.append(result)

    assert no_available_count == num_workers - 1, (
        f'Expected {num_workers - 1} NoAvailableCredentialsError exceptions.'
        f' Found {no_available_count} instead.'
    )

    assert len(acquired_credentials) == 1, (
        'Expected exactly one acquired credential, ' f'but found {len(acquired_credentials)}.'
    )

    assert acquired_credentials[0] == CredentialMetadata.from_orm(
        single_credential,
    ), 'The acquired credential does not match the expected credential.'


@pytest.mark.asyncio()
async def test_no_credentials_at_database(session):
    credentials_pool = PersistentCredentialsPool()

    with pytest.raises(NoCredentialsAtDatabaseError):
        await credentials_pool.acquire(max_retries=0)


@pytest.mark.asyncio()
async def test_credential_not_found_while_releasing(session):
    single_credential = Credential(username='test_user1', password='pass1', in_use=False)

    async with session() as _session:
        _session.add(single_credential)
        await _session.commit()

    credentials_pool = PersistentCredentialsPool()

    credential = await credentials_pool.acquire(max_retries=0)
    credential.username = 'changed_username'

    with pytest.raises(CredentialNotFoundError):
        await credentials_pool.release(credential)
