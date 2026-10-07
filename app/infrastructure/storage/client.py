"""S3-compatible storage client factory.

Isolates construction of the third-party boto3 S3 client so the repository
depends on an injected client instance, which keeps it unit-testable without
touching the network.

Connect and read timeouts are always applied (never an unbounded external call)
and credentials are read from the typed configuration, never hardcoded or
logged. ``host`` lets the client target a local emulator in non-production
environments; when it is ``None`` boto3 resolves the default AWS endpoint.
"""

from typing import Final

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.infrastructure.config import BucketConfig

DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
MAX_RETRY_ATTEMPTS: Final[int] = 3
S3_SERVICE_NAME: Final[str] = "s3"


def create_s3_client(
    config: BucketConfig,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> BaseClient:
    """Build an S3 client from the application configuration."""
    return boto3.client(
        S3_SERVICE_NAME,
        endpoint_url=config.host,
        region_name=config.region,
        aws_access_key_id=config.access_key.get_secret_value(),
        aws_secret_access_key=config.secret_key.get_secret_value(),
        config=Config(
            connect_timeout=timeout,
            read_timeout=timeout,
            retries={"max_attempts": MAX_RETRY_ATTEMPTS},
        ),
    )
