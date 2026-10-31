"""Shared RAG search service.

Orchestrates the single retrieval-augmented-generation pipeline shared by the
WhatsApp and online-chat endpoints, so the flow is defined once:

* look up the answer cache by the question fingerprint (hit returns early);
* load the user's prior history for the channel;
* generate the embedding for the question;
* query the vector store (only matches above the similarity threshold);
* ask the language model for an answer from the guide, history and matches;
* cache the answer when it is cacheable;
* persist the question/answer turn, refreshing the 30-minute history TTL.

The service is channel-agnostic: callers pass the :class:`HistoryChannel` and the
per-channel user key (WhatsApp number or online ``user_code``), keeping the
pipeline free of any endpoint-specific payload shape. The answer cache is shared
across channels because its key depends only on the question and the configured
versions. Every external interaction is delegated to the existing infrastructure
services, so this layer only coordinates the steps without duplicating their logic.
"""

from typing import Final

from app.application.cache import build_cache_key, build_fingerprint
from app.domain import (
    PATTERN_RESPONSE,
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
)
from app.infrastructure.config import FingerPrintConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai import OpenAIService
from app.infrastructure.pinecone import PineconeVectorRepository, VectorMatch
from app.infrastructure.redis import (
    HistoryChannel,
    RedisAnswerCacheRepository,
    RedisHistoryRepository,
)

logger = get_logger(__name__)

_LOGGED_KEY_LENGTH: Final[int] = 8


class SearchService:
    """Coordinate the shared RAG search pipeline for both channels."""

    def __init__(
        self,
        openai_service: OpenAIService,
        vector_repository: PineconeVectorRepository,
        history_repository: RedisHistoryRepository,
        answer_cache: RedisAnswerCacheRepository,
        fingerprint_config: FingerPrintConfig,
    ) -> None:
        self._openai = openai_service
        self._vectors = vector_repository
        self._history = history_repository
        self._answer_cache = answer_cache
        self._fingerprint_config = fingerprint_config

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> str:
        """Return the cached answer or run the full RAG pipeline."""
        logger.info("Starting RAG pipeline for channel='%s'", channel.value)
        cache_key = build_cache_key(build_fingerprint(question, self._fingerprint_config))
        cached_answer = await self._answer_cache.get(cache_key)
        if cached_answer is not None:
            logger.info(
                "Cache hit for channel='%s' (key='%s'), skipping RAG pipeline",
                channel.value,
                cache_key[:_LOGGED_KEY_LENGTH],
            )
            await self._persist_turn(channel, user_key, question, cached_answer)
            return cached_answer
        logger.info(
            "Cache miss for channel='%s' (key='%s')",
            channel.value,
            cache_key[:_LOGGED_KEY_LENGTH],
        )
        answer = await self._run_pipeline(channel, user_key, question)
        await self._store_if_cacheable(cache_key, answer)
        await self._persist_turn(channel, user_key, question, answer)
        logger.info("RAG pipeline completed, response ready for channel='%s'", channel.value)
        return answer

    async def _run_pipeline(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> str:
        """Generate the answer from history, vector matches and the language model."""
        history = await self._history.get_history(channel, user_key)
        logger.info("History loaded: %d messages for channel='%s'", len(history), channel.value)
        matches = await self._find_matches(question)
        logger.info("Vector search completed: %d relevant matches found", len(matches))
        payload = PayloadQuestionOpenIA(question=question, chat_historic=history)
        logger.info("Requesting chat answer from OpenAI")
        return await self._openai.generate_chat_answer(
            payload, self._to_phrases(matches)
        )

    async def _store_if_cacheable(self, cache_key: str, answer: str) -> None:
        """Cache the answer unless it is empty or the 'not found' fallback."""
        if not self._is_cacheable(answer):
            logger.info("Answer not cacheable (key='%s')", cache_key[:_LOGGED_KEY_LENGTH])
            return
        # The repository logs the successful write (or its failure).
        await self._answer_cache.set(cache_key, answer)

    async def _find_matches(self, question: str) -> list[VectorMatch]:
        """Embed the question and return the matches above the threshold."""
        embedding = await self._openai.generate_embedding_for_question(question)
        return await self._vectors.query(embedding)

    async def _persist_turn(
        self, channel: HistoryChannel, user_key: str, question: str, answer: str
    ) -> None:
        """Append the question and (when present) the answer to the history."""
        await self._history.append_message(
            channel, user_key, MessageHistoryItem(role=MessageRole.USER, text=question)
        )
        if answer:
            await self._history.append_message(
                channel,
                user_key,
                MessageHistoryItem(role=MessageRole.ASSISTANT, text=answer),
            )

    @staticmethod
    def _is_cacheable(answer: str) -> bool:
        stripped_answer = answer.strip()
        return bool(stripped_answer) and stripped_answer != PATTERN_RESPONSE.strip()

    @staticmethod
    def _to_phrases(matches: list[VectorMatch]) -> list[str]:
        """Extract the matched texts passed to the model as context snippets."""
        return [match.text for match in matches]
