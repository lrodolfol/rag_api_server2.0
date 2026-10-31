"""Answer-cache fingerprint and key generation.

Pure functions that turn a user question plus the ``finger_print`` configuration
into a deterministic cache key. They perform no I/O so the same input always
produces the same key, regardless of channel or user.
"""

import hashlib
import json
import re
import unicodedata
from typing import Final

from app.domain import CacheFingerprint
from app.infrastructure.config import FingerPrintConfig

_WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")


def normalize_question_finger_print(question: str) -> str:
    """Lowercase, strip accents and collapse whitespace so equivalent questions match."""
    decomposed = unicodedata.normalize("NFKD", question.strip().lower())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return _WHITESPACE_PATTERN.sub(" ", without_accents)


def build_fingerprint(question: str, config: FingerPrintConfig) -> CacheFingerprint:
    """Build the fingerprint for ``question`` using the configured versions."""
    return CacheFingerprint(
        prompt_version=config.prompt_version,
        rules_version=config.rules_version,
        model_capability=config.model_capability,
        normalized_text=normalize_question_finger_print(question),
    )


def build_cache_key(fingerprint: CacheFingerprint) -> str:
    """Return the SHA-256 hex digest of the fingerprint serialized as sorted JSON."""
    raw = json.dumps(fingerprint.model_dump(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
