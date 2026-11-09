"""Asynchronous client-record storage over an AWS S3 bucket.

Persists each client's registration as one line of the JSONL object of its
category (``client_services_{category_slug}.jsonl``) in the ``acha-local`` S3
bucket (region ``us-east-1``). Every operation reads and writes only the object
of the given category; the legacy ``client_services.jsonl`` object is never
touched. Updating a client is idempotent: the category object is read,
the line matching the client's ``user_code`` is replaced (or appended when new),
and the object is rewritten, so repeated registrations never accumulate duplicate
records. Deleting a client removes its line and rewrites the object only when a
record was actually removed.

The boto3 SDK is synchronous, so every blocking call is run in a worker thread
via :func:`asyncio.to_thread` to honour the application's async contract without
blocking the event loop. Bucket name and AWS credentials come from the typed
:class:`BucketConfig` which reads them from environment variables
``CLOUD_ACCESS_KEY`` and ``CLOUD_SECRET_KEY`` (never hardcoded); SDK failures are
translated into the domain :class:`ClientStorageError`, and no client data
(``user_code`` or record contents) is ever logged; logs only show the object key,
which carries the category slug.
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

CLIENT_RECORDS_OBJECT_KEY_TEMPLATE: Final[str] = "client_services_{category}.jsonl"
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

    async def save_client(
        self, registration: CompanyRegistrationRequest, category_slug: str
    ) -> None:
        """Create or update the client's record in its category JSONL object."""
        key = self._object_key(category_slug)
        records = await asyncio.to_thread(self._read_records, key)
        merged = self._merge_record(records, registration)
        body = self._serialize(merged)
        await asyncio.to_thread(self._put_records, key, body)
        logger.info(
            "Persisted client record to bucket '%s' (key '%s')", self._bucket_name, key
        )

    async def delete_client(self, user_code: str, category_slug: str) -> None:
        """Remove the client's record from its category JSONL object, if present.

        The object is only rewritten when a record was actually removed, so
        deleting an unknown client is a no-op.
        """
        key = self._object_key(category_slug)
        records = await asyncio.to_thread(self._read_records, key)
        remaining = self._remove_record(records, user_code)
        if len(remaining) == len(records):
            logger.info(
                "No client record to delete in bucket '%s' (key '%s')",
                self._bucket_name,
                key,
            )
            return
        body = self._serialize(remaining)
        await asyncio.to_thread(self._put_records, key, body)
        logger.info(
            "Deleted client record from bucket '%s' (key '%s')", self._bucket_name, key
        )

    @property
    def _bucket_name(self) -> str:
        bucket_name = self._config.bucket_name
        if not bucket_name:
            raise ClientStorageError("Bucket name is not configured")
        return bucket_name

    def _read_records(self, key: str) -> list[ClientRecord]:
        logger.info(
            "Reading client records from S3 bucket '%s' (key '%s')", self._bucket_name, key
        )
        try:
            response = self._client.get_object(Bucket=self._bucket_name, Key=key)
            payload = response["Body"].read().decode("utf-8")
        except ClientError as error:
            if self._is_missing_object(error):
                logger.info("No existing records found in S3 bucket '%s'", self._bucket_name)
                return []
            logger.exception("Failed to read client records from storage")
            raise ClientStorageError("Failed to read client records") from error
        except BotoCoreError as error:
            logger.exception("Failed to read client records from storage")
            raise ClientStorageError("Failed to read client records") from error
        return self._parse(payload)

    def _put_records(self, key: str, body: str) -> None:
        logger.info(
            "Writing client records to S3 bucket '%s' (key '%s')", self._bucket_name, key
        )
        try:
            self._client.put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=body.encode("utf-8"),
                ContentType=JSONL_CONTENT_TYPE,
            )
        except (BotoCoreError, ClientError) as error:
            logger.exception("Failed to persist client record to storage")
            raise ClientStorageError("Failed to persist client record") from error

    @staticmethod
    def _object_key(category_slug: str) -> str:
        """Return the JSONL object key of a category (raises on a blank slug)."""
        if not category_slug.strip():
            raise ClientStorageError("Category slug is required to access client records")
        return CLIENT_RECORDS_OBJECT_KEY_TEMPLATE.format(category=category_slug)

    @staticmethod
    def _merge_record(
        records: list[ClientRecord], registration: CompanyRegistrationRequest
    ) -> list[ClientRecord]:
        kept = ClientStorageRepository._remove_record(records, registration.user_code)
        kept.append(registration.model_dump(mode="json"))
        return kept

    @staticmethod
    def _remove_record(
        records: list[ClientRecord], user_code: str
    ) -> list[ClientRecord]:
        return [record for record in records if record.get("user_code") != user_code]

    @staticmethod
    def _serialize(records: list[ClientRecord]) -> str:
        if not records:
            return ""
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _parse(payload: str) -> list[ClientRecord]:
        return [json.loads(line) for line in payload.splitlines() if line.strip()]

    @staticmethod
    def _is_missing_object(error: ClientError) -> bool:
        code = error.response.get("Error", {}).get("Code", "")
        return code in _MISSING_OBJECT_ERROR_CODES
