"""Shared RAG search service.

Orchestrates the single retrieval-augmented-generation pipeline shared by the
WhatsApp and online-chat endpoints, so the flow is defined once:

* look up the exact answer cache by the question fingerprint; the stored
  ``{"respostas": [...]}`` JSON is parsed into a :class:`ChatAnswer` (hit
  returns early, without embedding the question or consulting the semantic
  cache; a corrupted value is logged and treated as a miss);
* generate the embedding of the normalized question once (reused downstream);
* look up the semantic cache with that embedding; only matches whose similarity
  reaches ``SIMILARITY_THRESHOLD`` count, and their answers are merged (most
  similar first, without duplicated items); a hit returns the merged answer and
  also stores its JSON in the exact cache under the current key;
* load the user's prior history for the channel;
* query the vector store with that embedding (only matches above the
  similarity threshold);
* ask the language model for a :class:`ChatAnswer` from the guide, history and
  matches;
* store the answer JSON in the exact and semantic caches when it is cacheable;
* persist the question/answer turn (items joined into readable text),
  refreshing the 30-minute history TTL;
* return the messages for the client: a random intro followed by each item, or
  a single random 'not found' message when there are no items.

The service is channel-agnostic: callers pass the :class:`HistoryChannel` and the
per-channel user key (WhatsApp number or online ``user_code``), keeping the
pipeline free of any endpoint-specific payload shape. Both answer caches are
shared across channels because they depend only on the question and the
configured versions. Every external interaction is delegated to the existing
infrastructure and cache services, so this layer only coordinates the steps
without duplicating their logic.
"""
from random import choice
from typing import Final

from app.application.cache import (
    SemanticCacheService,
    build_cache_key,
    build_fingerprint,
    is_cacheable_answer,
)
from app.domain import (
    CacheFingerprint,
    ChatAnswer,
    InvalidChatAnswerError,
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
    SemanticCacheMatch,
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
_NOT_FOUND_MESSAGES: Final[tuple[str, ...]] = (
    "Não encontrei resultados para sua busca. Que tal tentar de outra forma?",
    "Poxa, não encontrei opções relacionadas à sua pesquisa.",
    "Não localizei estabelecimentos que correspondam à sua busca.",
    "Ops, não encontrei nenhuma referência, mas podemos tentar outro tema!",
    "Que tal tentar com outras palavras?",
    "Talvez utilizando outros termos eu consiga encontrar o que procura.",
    "Dessa vez você não teve sorte na busca. Vamos tentar com outra busca?",
    "Não encontrei o que você procura desta vez. Vamos tentar novamente?",
)
_ANSWER_MESSAGES: Final[tuple[str, ...]] = (
    "Encontrei algumas opções que podem atender à sua necessidade!",
    "Boa notícia! Encontrei alguns estabelecimentos para você.",
    "Separei algumas opções que podem ser interessantes para você.",
    "Encontrei alguns resultados relacionados à sua busca. Confira!",
    "Tenho algumas sugestões que podem ajudar você!",
    "Olha só o que encontrei para você!",
    "Encontrei algumas opções interessantes. Vamos conferir?",
    "Achei algumas alternativas que podem ser exatamente o que você procura!",
    "Tenho algumas sugestões para facilitar sua busca.",
    "Dá uma olhada nessas opções que encontrei!",
    "Encontrei opções que podem atender você!",
    "Localizei certas respostas relacionadas à sua busca.",
    "Encontrei boas opções próximas ao que você procura.",
    "Separei alguns serviços que podem ser úteis para você.",
    "Encontrei uma opção que pode atender à sua necessidade!",
    "Localizei resultados relevantes para sua busca.",
    "Essas opções podem ajudar você.",
)


class SearchService:
    """Coordinate the shared RAG search pipeline for both channels."""

    SIMILARITY_THRESHOLD: Final[float] = 0.81

    def __init__(
        self,
        openai_service: OpenAIService,
        vector_repository: PineconeVectorRepository,
        history_repository: RedisHistoryRepository,
        answer_cache: RedisAnswerCacheRepository,
        semantic_cache: SemanticCacheService,
        fingerprint_config: FingerPrintConfig,
    ) -> None:
        self._openai = openai_service
        self._vectors = vector_repository
        self._history = history_repository
        self._answer_cache = answer_cache
        self._semantic_cache = semantic_cache
        self._fingerprint_config = fingerprint_config

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> list[str]:
        """Return the client messages from a cached answer or the full RAG pipeline."""
        logger.info("Starting RAG pipeline for channel='%s'", channel.value)
        fingerprint = build_fingerprint(question, self._fingerprint_config)
        cache_key = build_cache_key(fingerprint)
        answer = await self._get_cached_answer(channel, cache_key)
        if answer is None:
            answer = await self._answer_on_cache_miss(
                channel, user_key, question, fingerprint, cache_key
            )
        await self._persist_turn(channel, user_key, question, answer)
        return self._to_client_messages(answer)

    @staticmethod
    def _to_client_messages(answer: ChatAnswer) -> list[str]:
        """Prefix the items with a random intro, or return a random 'not found' message."""
        if answer.is_empty():
            return [choice(_NOT_FOUND_MESSAGES)]
        return [choice(_ANSWER_MESSAGES), *answer.respostas]

    async def _get_cached_answer(
        self, channel: HistoryChannel, cache_key: str
    ) -> ChatAnswer | None:
        """Return the exact-match cached answer, logging the hit or miss."""
        raw_answer = await self._answer_cache.get(cache_key)
        cached_answer = None if raw_answer is None else self._parse_cached(raw_answer, "exact")
        outcome = "hit, skipping RAG pipeline" if cached_answer is not None else "miss"
        logger.info(
            "Cache %s for channel='%s' (key='%s')",
            outcome,
            channel.value,
            cache_key[:_LOGGED_KEY_LENGTH],
        )
        return cached_answer

    @staticmethod
    def _parse_cached(raw_answer: str, cache_name: str) -> ChatAnswer | None:
        """Parse a cached answer JSON; a corrupted value is logged and ignored (miss)."""
        try:
            return ChatAnswer.from_json(raw_answer)
        except InvalidChatAnswerError:
            logger.warning("Ignoring invalid answer JSON stored in the %s cache", cache_name)
            return None

    async def _answer_on_cache_miss(
        self,
        channel: HistoryChannel,
        user_key: str,
        question: str,
        fingerprint: CacheFingerprint,
        cache_key: str,
    ) -> ChatAnswer:
        """Answer from the semantic cache or, on a miss, from the RAG pipeline."""
        # Embedded once from the normalized text and reused by every later step.
        embedding = await self._openai.generate_embedding_for_question(
            fingerprint.normalized_text
        )
        semantic_answer = await self._answer_from_semantic_cache(
            channel, cache_key, fingerprint, embedding
        )
        if semantic_answer is not None:
            return semantic_answer
        answer = await self._run_pipeline(channel, user_key, question, embedding)
        await self._store_answer(cache_key, fingerprint, question, answer, embedding)
        logger.info("RAG pipeline completed, response ready for channel='%s'", channel.value)
        return answer

    async def _answer_from_semantic_cache(
        self,
        channel: HistoryChannel,
        cache_key: str,
        fingerprint: CacheFingerprint,
        embedding: list[float],
    ) -> ChatAnswer | None:
        """Return the merged answer of the matches above the threshold, also caching it."""
        matches = await self._semantic_cache.find_answer(fingerprint, embedding)
        semantic_answer = self.threshold_evaluate(matches)
        short_key = cache_key[:_LOGGED_KEY_LENGTH]
        if semantic_answer is None:
            logger.info(
                "Semantic cache miss for channel='%s' (key='%s')", channel.value, short_key
            )
            return None
        logger.info(
            "Semantic cache hit for channel='%s' (key='%s'), skipping RAG pipeline",
            channel.value,
            short_key,
        )
        await self._answer_cache.set(cache_key, semantic_answer.to_json())
        return semantic_answer

    @classmethod
    def threshold_evaluate(cls, matches: list[SemanticCacheMatch]) -> ChatAnswer | None:
        """Merge the answers at or above the threshold, or ``None`` if no item is accepted."""
        accepted_answers: list[ChatAnswer] = []
        for match in matches:
            if match.similarity < cls.SIMILARITY_THRESHOLD:
                continue
            answer = cls._parse_cached(match.response, "semantic")
            if answer is not None:
                accepted_answers.append(answer)
        merged = ChatAnswer.merge(accepted_answers)
        return None if merged.is_empty() else merged

    async def _run_pipeline(
        self,
        channel: HistoryChannel,
        user_key: str,
        question: str,
        embedding: list[float],
    ) -> ChatAnswer:
        """Generate the answer from history, vector matches and the language model."""
        history = await self._history.get_history(channel, user_key)
        logger.info("History loaded: %d messages for channel='%s'", len(history), channel.value)
        matches = await self._find_matches(embedding)
        logger.info("Vector search completed: %d relevant matches found", len(matches))
        payload = PayloadQuestionOpenIA(question=question, chat_historic=history)
        logger.info("Requesting chat answer from OpenAI")
        return await self._openai.generate_chat_answer(
            payload, self._to_phrases(matches)
        )

    async def _store_answer(
        self,
        cache_key: str,
        fingerprint: CacheFingerprint,
        question: str,
        answer: ChatAnswer,
        embedding: list[float],
    ) -> None:
        """Store the LLM answer JSON in both caches unless it is not cacheable."""
        if not is_cacheable_answer(answer):
            logger.info("Answer not cacheable (key='%s')", cache_key[:_LOGGED_KEY_LENGTH])
            return
        # The repositories log the successful writes (or their failures).
        await self._answer_cache.set(cache_key, answer.to_json())
        await self._semantic_cache.store(fingerprint, question, answer, embedding)

    async def _find_matches(self, embedding: list[float]) -> list[VectorMatch]:
        """Return the vector-store matches above the threshold for ``embedding``."""
        return await self._vectors.query(embedding)

    async def _persist_turn(
        self, channel: HistoryChannel, user_key: str, question: str, answer: ChatAnswer
    ) -> None:
        """Append the question and (when it has items) the answer text to the history."""
        await self._history.append_message(
            channel, user_key, MessageHistoryItem(role=MessageRole.USER, text=question)
        )
        if not answer.is_empty():
            await self._history.append_message(
                channel,
                user_key,
                MessageHistoryItem(role=MessageRole.ASSISTANT, text=answer.as_text()),
            )

    @staticmethod
    def _to_phrases(matches: list[VectorMatch]) -> list[str]:
        """Extract the matched texts passed to the model as context snippets."""
        return [match.text for match in matches]
