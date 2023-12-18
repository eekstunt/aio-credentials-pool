import asyncio
import logging

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
async def test_acquiring_single_credential_without_retries(session):
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
        f'Expected {num_workers - 1} NoAvailableCredentialsError exceptions.' f' Found {no_available_count} instead.'
    )

    assert len(acquired_credentials) == 1, (
        'Expected exactly one acquired credential, ' f'but found {len(acquired_credentials)}.'
    )

    assert acquired_credentials[0] == CredentialMetadata.from_orm(
        single_credential,
    ), 'The acquired credential does not match the expected credential.'


@pytest.mark.asyncio()
async def test_acquiring_single_credential_with_retries(session):
    async def acquire_and_release(pool: PersistentCredentialsPool) -> None:
        credential = await pool.acquire(max_retries=5, min_wait=0.05)
        await asyncio.sleep(0.01)
        await pool.release(credential)

    single_credential = Credential(username='test_user4', password='pass4', in_use=False)

    async with session() as _session:
        _session.add(single_credential)
        await _session.commit()

    credentials_pool = PersistentCredentialsPool()

    num_workers = 3
    tasks = [acquire_and_release(credentials_pool) for _ in range(num_workers)]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert results == [None] * num_workers


@pytest.mark.asyncio()
async def test_acquiring_and_releasing_coherence(session, caplog):
    async def acquire_and_release(pool: PersistentCredentialsPool) -> None:
        cred = await pool.acquire(max_retries=5, min_wait=0.05)
        await asyncio.sleep(0.01)
        await pool.release(cred)

    def check_log_release(log_msg: str, cred: CredentialMetadata, released: bool) -> bool:
        log_content = log_msg.split('Credential released: ')
        if len(log_content) == 2 and log_content[1] == repr(cred):
            assert not released
            released = True
        return released

    def check_log_acquire(log_msg: str, cred: CredentialMetadata, released: bool) -> bool:
        log_content = log_msg.split('Credential acquired: ')
        if len(log_content) == 2 and log_content[1] == repr(cred):
            assert released
            released = False
        return released

    caplog.set_level(level=logging.INFO)

    credentials = [
        Credential(username='test_user1', password='pass1', in_use=False),
        Credential(username='test_user2', password='pass2', in_use=False),
        Credential(username='test_user3', password='pass3', in_use=False),
    ]

    credential_metadata = [CredentialMetadata.from_orm(cred) for cred in credentials]

    async with session() as _session:
        for credential in credentials:
            _session.add(credential)
        await _session.commit()

    credentials_pool = PersistentCredentialsPool()

    num_workers = 7
    tasks = [acquire_and_release(credentials_pool) for _ in range(num_workers)]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert results == [None] * num_workers

    credential_released = [True] * len(credentials)

    for log_message in caplog.messages:
        for i, metadata in enumerate(credential_metadata):
            credential_released[i] = check_log_release(log_message, metadata, credential_released[i])
            credential_released[i] = check_log_acquire(log_message, metadata, credential_released[i])


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
