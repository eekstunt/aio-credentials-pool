# aio-credentials-pool

## Objective

The objective of aio-credentials-pools is to provide a robust and efficient system on top of asyncio
for managing a pool of credentials, accessible and usable by multiple concurrent consumers or workers.
This system is designed with a focus on concurrency and resource management, ensuring smooth operation under varying workloads.

## Implementations and Design Choices

The project offers two realizations of credential pools:

### InMemoryCredentialsPool

The `InMemoryCredentialsPool` class manages credentials in memory. It utilizes asyncio locks to handle concurrent access, ensuring safe acquisition and release of credentials.

It utilizes a FIFO strategy, organizing credentials solely based on their order of arrival.
While this method ensures a fair distribution of credentials,
it doesn't account for variations in usage frequency or quantity,
potentially overlooking the disparity in their actual utilization.

### PersistentCredentialsPool

The `PersistentCredentialsPool` class interacts with a PostgreSQL database to manage credentials persistently. It employs database queries,
utilizing the `select for update` and `skip locked` functionalities, to acquire available credentials and updates their usage status upon release.

It implements a usage-based utilization strategy for credential management. 
This strategy revolves around dynamically prioritizing credentials based on their last usage timestamp. 
By tracking the date_last_usage, the system ensures a fair distribution of usage among available credentials. 
It aims to prevent overuse of specific credentials by favoring those that have been idle for longer periods, thus promoting efficient resource utilization. 

### Worker
Additionally, the project encapsulates worker logic, where multiple workers engage in acquiring and releasing credentials concurrently. Each worker acquires a credential, simulates work, and responsibly releases it back to the pool. This implementation guarantees graceful handling of shutdown signals, ensuring that workers release all acquired credentials before termination, maintaining system stability and data integrity.

## Running the Project

To run the aio-credentials-pool, ensure you have `make` and `Docker` installed on your system.

```bash
git clone https://github.com/eekstunt/aio-credentials-pool.git
cd aio-credentials-pool
make run
```

After building and running the project, it's important to review the logs for both the in-memory and persistent implementations using the following commands:

```bash
docker logs in_memory_credentials_pool
docker logs persistent_credentials_pool
```
These logs contain messages related to the acquisition and release of credentials.

## How to run tests

Run tests using the following command:

```bash
make test
