"""Asynchronous OpenAI integration service.

Provides the three capabilities the RAG pipeline needs from the language-model
provider:

* moderating client-submitted content (to stop inappropriate ingestion),
* generating embeddings (for chunks and for an isolated question),
* generating a chat answer from the guide, history, question and matches.

Model names and the chat ``input_guide`` always come from the typed
configuration (never hardcoded). Every provider failure is translated into the
domain :class:`OpenIaException`; the API key and raw provider payloads are never
logged.
"""

import json
from tokenize import String
from typing import Final

from openai import AsyncOpenAI, OpenAIError

from app.domain import EmbeddingRecord, INPUT_GUIDE, OpenIaException, PayloadQuestionOpenIA, QUERY_PREFIX
from app.infrastructure.config import OpenAIConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai.models import ModerationResult

logger = get_logger(__name__)

ChatMessage = dict[str, str]

_MODERATION_PROMPT: Final[str] = (
    "Você é um assistente especialista em análise de informações enviadas por "
    "clientes. Dadas as informações abaixo, verifique se há qualquer tipo de "
    "xingamento ou conteúdo inapropriado.\n"
    "Informações do cliente:\n{content}\n\n"
    "Responda exclusivamente em JSON válido, sem texto adicional, no formato: "
    '{{"insult": true/false, "insult_text": "trecho ofensivo ou vazio"}}'
)


class OpenAIService:
    """Async wrapper around the OpenAI provider used by the RAG pipeline."""

    def __init__(self, client: AsyncOpenAI, config: OpenAIConfig) -> None:
        self._client = client
        self._config = config

    async def moderate(self, content: str) -> ModerationResult:
        """Check client content for insults/inappropriate text."""
        logger.info("Sending moderation request to OpenAI")
        prompt = _MODERATION_PROMPT.format(content=content)
        raw_answer = await self._create_response([{"role": "system", "content": prompt}])
        logger.info("OpenAI moderation response received")
        return self._parse_moderation(raw_answer)

    async def generate_embeddings_from_chunks(
        self, chunks: list[str]
    ) -> list[EmbeddingRecord]:
        """Generate one :class:`EmbeddingRecord` per text chunk."""
        logger.info("Requesting embeddings from OpenAI for %d chunks", len(chunks))
        records: list[EmbeddingRecord] = []
        for chunk in chunks:
            vector = await self._generate_vector(chunk)
            records.append(EmbeddingRecord(text=chunk, vector=vector))
        logger.info("OpenAI embeddings generated: %d records", len(records))
        return records

    async def generate_embedding_for_question(self, question: str) -> list[float]:
        """Generate the embedding vector for an isolated question."""
        if not question.strip():
            return []
        logger.info("Requesting question embedding from OpenAI")
        enriched = f"{QUERY_PREFIX}{question}" if QUERY_PREFIX else question
        vector = await self._generate_vector(enriched)
        logger.info("Question embedding received from OpenAI")
        return vector

    async def generate_chat_answer(
        self, payload: PayloadQuestionOpenIA, phrases: list[str]
    ) -> str:
        """Generate the chat answer from the guide, history, question and matches."""
        if payload.is_invalid():
            return ""
        logger.info("Sending chat completion request to OpenAI (context_phrases=%d)", len(phrases))
        answer = await self._create_response(self._build_chat_input(payload, phrases))
        if not answer:
            raise OpenIaException("No answer returned from the OpenAI provider")
        logger.info("Chat completion response received from OpenAI")
        return answer

    async def _generate_vector(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(
                input=text, model=self._config.model_embeddings
            )
        except OpenAIError as error:
            logger.exception("OpenAI embedding request failed")
            raise OpenIaException("Failed to generate embedding") from error
        return response.data[0].embedding

    async def _create_response(self, chat_input: list[ChatMessage]) -> str:
        try:
            response = await self._client.responses.create(
                model=self._config.model_chat, input=chat_input
            )
        except OpenAIError as error:
            logger.exception("OpenAI chat request failed")
            raise OpenIaException("Failed to generate response") from error
        return response.output_text if response else ""

    def _build_chat_input(
        self, payload: PayloadQuestionOpenIA, phrases: list[str]
    ) -> list[ChatMessage]:
        return [
            {"role": "system", "content": INPUT_GUIDE},
            *self._build_history(payload),
            {"role": "user", "content": f"Pergunta: {payload.question}"},
            {"role": "system", "content": f"Trechos: {phrases}"},
        ]

    def _build_history(self, payload: PayloadQuestionOpenIA) -> list[ChatMessage]:
        return [
            {"role": "user" if item.is_user else "assistant", "content": item.text}
            for item in payload.chat_historic
        ]

    def _parse_moderation(self, raw_answer: str) -> ModerationResult:
        try:
            data = json.loads(self._strip_code_fence(raw_answer))
        except (json.JSONDecodeError, TypeError) as error:
            logger.error("Moderation response was not valid JSON")
            raise OpenIaException("Invalid moderation response") from error
        return ModerationResult(
            insult=bool(data.get("insult", False)),
            insult_text=str(data.get("insult_text", "")),
        )

    @staticmethod
    def _strip_code_fence(raw_answer: str) -> str:
        text = raw_answer.strip()
        if not text.startswith("```"):
            return text
        without_fence = text.strip("`")
        if without_fence.startswith("json"):
            without_fence = without_fence[len("json") :]
        return without_fence.strip()
