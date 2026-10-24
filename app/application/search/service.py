"""Shared RAG search service.

Orchestrates the single retrieval-augmented-generation pipeline shared by the
WhatsApp and online-chat endpoints, so the flow is defined once:

* load the user's prior history for the channel;
* generate the embedding for the question;
* query the vector store (only matches above the similarity threshold);
* ask the language model for an answer from the guide, history and matches;
* persist the question/answer turn, refreshing the 30-minute history TTL.

The service is channel-agnostic: callers pass the :class:`HistoryChannel` and the
per-channel user key (WhatsApp number or online ``user_code``), keeping the
pipeline free of any endpoint-specific payload shape. Every external interaction
is delegated to the existing infrastructure services, so this layer only
coordinates the steps without duplicating their logic.
"""

from app.domain import MessageHistoryItem, MessageRole, PayloadQuestionOpenIA
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai import OpenAIService
from app.infrastructure.pinecone import PineconeVectorRepository, VectorMatch
from app.infrastructure.redis import HistoryChannel, RedisHistoryRepository

logger = get_logger(__name__)


class SearchService:
    """Coordinate the shared RAG search pipeline for both channels."""

    def __init__(
        self,
        openai_service: OpenAIService,
        vector_repository: PineconeVectorRepository,
        history_repository: RedisHistoryRepository,
    ) -> None:
        self._openai = openai_service
        self._vectors = vector_repository
        self._history = history_repository

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> str:
        """Run the full RAG pipeline and return the generated answer."""
        logger.info("Starting RAG pipeline for channel='%s'", channel.value)
        history = await self._history.get_history(channel, user_key)
        logger.info("History loaded: %d messages for channel='%s'", len(history), channel.value)
        matches = await self._find_matches(question)
        logger.info("Vector search completed: %d relevant matches found", len(matches))
        payload = PayloadQuestionOpenIA(question=question, chat_historic=history)
        logger.info("Requesting chat answer from OpenAI")
        answer = await self._openai.generate_chat_answer(
            payload, self._to_phrases(matches)
        )
        await self._persist_turn(channel, user_key, question, answer)
        logger.info("RAG pipeline completed, response ready for channel='%s'", channel.value)
        return answer

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
    def _to_phrases(matches: list[VectorMatch]) -> list[str]:
        """Extract the matched texts passed to the model as context snippets."""
        return [match.text for match in matches]
