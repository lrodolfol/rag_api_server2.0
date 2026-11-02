"""PostgreSQL connection factory.

Opens one asynchronous :class:`psycopg.AsyncConnection` per operation from the
typed configuration. Callers use it as ``async with await
open_postgres_connection(config) as connection``: the transaction is committed
on success, rolled back on error and the connection is always closed.

The password is read from the typed configuration, never hardcoded or logged.
"""

from typing import Final

from psycopg import AsyncConnection

from app.infrastructure.config import PostgresConfig

CONNECT_TIMEOUT_SECONDS: Final[int] = 5


async def open_postgres_connection(config: PostgresConfig) -> AsyncConnection:
    """Open an async PostgreSQL connection from the application configuration."""
    return await AsyncConnection.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password.get_secret_value(),
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    )
