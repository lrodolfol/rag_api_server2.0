"""S3-compatible storage integration package.

Exposes the async client-record repository used by the company registration
flow, the factory that builds the underlying boto3 client from the typed
configuration, and the JSONL object key the records are stored under.
"""

from app.infrastructure.storage.client import create_s3_client
from app.infrastructure.storage.repository import (
    CLIENT_RECORDS_OBJECT_KEY,
    ClientStorageRepository,
)

__all__ = [
    "CLIENT_RECORDS_OBJECT_KEY",
    "ClientStorageRepository",
    "create_s3_client",
]
