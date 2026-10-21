"""Asynchronous client-record storage over an AWS S3 bucket.

Persists each client's registration as one line of a single JSONL object
(``client_services.jsonl``) in the ``acha-local`` S3 bucket (region
``us-east-1``). Updating a client is idempotent: the existing object is read,
the line matching the client's ``user_code`` is replaced (or appended when new),
and the object is rewritten, so repeated registrations never accumulate duplicate
records.

The boto3 SDK is synchronous, so every blocking call is run in a worker thread
via :func:`asyncio.to_thread` to honour the application's async contract without
blocking the event loop. Bucket name and AWS credentials come from the typed
:class:`BucketConfig` which reads them from environment variables
``CLOUD_ACCESS_KEY`` and ``CLOUD_SECRET_KEY`` (never hardcoded); SDK failures are
translated into the domain :class:`ClientStorageError`, and no client data
(``user_code`` or record contents) is ever logged.
"""

import asyncio
import json
from typing import Final

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.domain import ClientStorageError, CompanyRegistrationRequest
from app.infrastructure.config import BucketConfig
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

CLIENT_RECORDS_OBJECT_KEY: Final[str] = "client_services.jsonl"
JSONL_CONTENT_TYPE: Final[str] = "application/x-ndjson"
_MISSING_OBJECT_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {"NoSuchKey", "NoSuchBucket", "404"}
)

ClientRecord = dict[str, object]


class ClientStorageRepository:
    """Async repository that stores client records as JSONL in a bucket."""

    def __init__(self, client: BaseClient, config: BucketConfig) -> None:
        self._client = client
        self._config = config

    async def save_client(self, registration: CompanyRegistrationRequest) -> None:
        """Create or update the client's record in the JSONL bucket object."""
        records = await asyncio.to_thread(self._read_records)
        merged = self._merge_record(records, registration)
        body = self._serialize(merged)
        await asyncio.to_thread(self._put_records, body)
        logger.info(
            "Persisted client record to bucket '%s' (key '%s')",
            self._bucket_name,
            CLIENT_RECORDS_OBJECT_KEY,
        )

    @property
    def _bucket_name(self) -> str:
        bucket_name = self._config.bucket_name
        if not bucket_name:
            raise ClientStorageError("Bucket name is not configured")
        return bucket_name

    def _read_records(self) -> list[ClientRecord]:
        try:
            response = self._client.get_object(
                Bucket=self._bucket_name, Key=CLIENT_RECORDS_OBJECT_KEY
            )
            payload = response["Body"].read().decode("utf-8")
        except ClientError as error:
            if self._is_missing_object(error):
                return []
            logger.exception("Failed to read client records from storage")
            raise ClientStorageError("Failed to read client records") from error
        except BotoCoreError as error:
            logger.exception("Failed to read client records from storage")
            raise ClientStorageError("Failed to read client records") from error
        return self._parse(payload)

    def _put_records(self, body: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket_name,
                Key=CLIENT_RECORDS_OBJECT_KEY,
                Body=body.encode("utf-8"),
                ContentType=JSONL_CONTENT_TYPE,
            )
        except (BotoCoreError, ClientError) as error:
            logger.exception("Failed to persist client record to storage")
            raise ClientStorageError("Failed to persist client record") from error

    @staticmethod
    def _merge_record(
        records: list[ClientRecord], registration: CompanyRegistrationRequest
    ) -> list[ClientRecord]:
        user_code = registration.user_code
        kept = [
            record for record in records if record.get("user_code") != user_code
        ]
        kept.append(registration.model_dump(mode="json"))
        return kept

    @staticmethod
    def _serialize(records: list[ClientRecord]) -> str:
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _parse(payload: str) -> list[ClientRecord]:
        return [json.loads(line) for line in payload.splitlines() if line.strip()]

    @staticmethod
    def _is_missing_object(error: ClientError) -> bool:
        code = error.response.get("Error", {}).get("Code", "")
        return code in _MISSING_OBJECT_ERROR_CODES
