"""Asynchronous OpenAI integration service.

Provides the three capabilities the RAG pipeline needs from the language-model
provider:

* moderating client-submitted content (to stop inappropriate ingestion) and
  classifying it into a knowledge-base category,
* classifying a user question into one of the knowledge-base categories,
* generating embeddings (for chunks and for an isolated question),
* generating a chat answer from the guide, history, question and matches.

Model names and the chat ``input_guide`` always come from the typed
configuration (never hardcoded). Every provider failure is translated into the
domain :class:`OpenIaException`; the API key and raw provider payloads are never
logged.
"""

import json
from typing import Any, Final

from openai import AsyncOpenAI, OpenAIError

from app.domain import (
    INPUT_GUIDE,
    QUERY_PREFIX,
    ChatAnswer,
    EmbeddingRecord,
    InvalidChatAnswerError,
    OpenIaException,
    PayloadQuestionOpenIA,
)
from app.infrastructure.config import OpenAIConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai.models import ModerationResult

logger = get_logger(__name__)

ChatMessage = dict[str, str]
TextFormat = dict[str, Any]

# JSON mode of the Responses API: the model must return a JSON object.
_JSON_TEXT_FORMAT: Final[TextFormat] = {"format": {"type": "json_object"}}

_MODERATION_PROMPT: Final[str] = (
    "Você é um assistente especialista em análise de informações enviadas por "
    "clientes. Dadas as informações abaixo, verifique se há qualquer tipo de "
    "xingamento ou conteúdo inapropriado e classifique o serviço do cliente em "
    "uma categoria.\n"
    "Informações do cliente:\n{content}\n\n"
    "{category_rule}\n\n"
    "Responda exclusivamente em JSON válido, sem texto adicional, no formato: "
    '{{"insult": true/false, "insult_text": "trecho ofensivo ou vazio", '
    '"categoria": "nome da categoria"}}'
)

_NEW_CATEGORY_RULE: Final[str] = (
    "uma única categoria nova, curta, em português e em letras maiúsculas."
)

_CATEGORY_RULE_WITH_LIST: Final[str] = (
    "Categorias disponíveis (uma por linha):\n{categories}\n\n"
    "Escolha exatamente uma categoria da lista acima, escrita exatamente como "
    "está na lista. Se nenhuma servir, sugira " + _NEW_CATEGORY_RULE
)

_CATEGORY_RULE_WITHOUT_LIST: Final[str] = (
    "Sugira para o serviço " + _NEW_CATEGORY_RULE
)

# The question goes in a separate user message, never inside these instructions.
_CLASSIFICATION_PROMPT: Final[str] = (
    "Você é um assistente que classifica perguntas de usuários que procuram "
    "estabelecimentos, produtos e serviços.\n"
    "Categorias disponíveis (uma por linha):\n{categories}\n\n"
    "Escolha exatamente uma categoria da lista acima, a mais relevante para a "
    "pergunta do usuário, escrita exatamente como está na lista. Se nenhuma "
    "categoria servir, responda com a categoria vazia.\n"
    "Responda exclusivamente em JSON válido, sem texto adicional, no formato: "
    '{{"categoria": "nome da categoria ou vazio"}}'
)


class OpenAIService:
    """Async wrapper around the OpenAI provider used by the RAG pipeline."""

    def __init__(self, client: AsyncOpenAI, config: OpenAIConfig) -> None:
        self._client = client
        self._config = config

    async def moderate(self, content: str, categories: list[str]) -> ModerationResult:
        """Check client content for insults and classify it into a category.

        The LLM picks one of ``categories`` or, when none fits (or the list is
        empty), suggests a new one. ``category`` is ``""`` when none is returned.
        """
        logger.info("Sending moderation request to OpenAI (categories=%d)", len(categories))
        prompt = _MODERATION_PROMPT.format(
            content=content, category_rule=self._build_category_rule(categories)
        )
        raw_answer = await self._create_response([{"role": "system", "content": prompt}])
        result = self._parse_moderation(raw_answer)
        logger.info("OpenAI moderation response received (category='%s')", result.category)
        return result

    async def classify_question(self, question: str, categories: list[str]) -> str:
        """Return the category (from ``categories``) most relevant to ``question``.

        Returns ``""`` when the model finds no suitable category. Raises
        :class:`OpenIaException` when the provider fails or the answer is not JSON.
        """
        logger.info("Sending question classification request to OpenAI (categories=%d)", len(categories))
        prompt = _CLASSIFICATION_PROMPT.format(categories="\n".join(categories))
        raw_answer = await self._create_response(
            [{"role": "system", "content": prompt}, {"role": "user", "content": question}],
            text_format=_JSON_TEXT_FORMAT,
        )
        data = self._load_json_object(raw_answer, "Question classification")
        category = str(data.get("categoria") or "").strip()
        logger.info("OpenAI question classification received (category='%s')", category)
        return category

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
    ) -> ChatAnswer:
        """Generate the chat answer from the guide, history, question and matches."""
        if payload.is_invalid():
            return ChatAnswer()
        logger.info("Sending chat completion request to OpenAI (context_phrases=%d)", len(phrases))
        raw_answer = await self._create_response(
            self._build_chat_input(payload, phrases), text_format=_JSON_TEXT_FORMAT
        )
        answer = self._parse_chat_answer(raw_answer)
        logger.info("Chat completion response received from OpenAI (items=%d)", len(answer.respostas))
        return answer

    async def _generate_vector(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(
                input=text, model=self._config.default_model_embeddings
            )
        except OpenAIError as error:
            logger.exception("OpenAI embedding request failed")
            raise OpenIaException("Failed to generate embedding") from error
        return response.data[0].embedding

    async def _create_response(
        self, chat_input: list[ChatMessage], text_format: TextFormat | None = None
    ) -> str:
        options = {"text": text_format} if text_format is not None else {}
        try:
            response = await self._client.responses.create(
                model=self._config.model_chat, input=chat_input, **options
            )
        except OpenAIError as error:
            logger.exception("OpenAI chat request failed")
            raise OpenIaException("Failed to generate response") from error
        return response.output_text if response else ""

    def _parse_chat_answer(self, raw_answer: str) -> ChatAnswer:
        if not raw_answer.strip():
            logger.warning("OpenAI returned an empty chat answer")
            return ChatAnswer()
        try:
            return ChatAnswer.from_json(self._strip_code_fence(raw_answer))
        except InvalidChatAnswerError:
            logger.error("Chat answer was not valid answer JSON, treating it as not found")
            return ChatAnswer()

    def _build_chat_input(
        self, payload: PayloadQuestionOpenIA, phrases: list[str]
    ) -> list[ChatMessage]:
        knowledge = "\n\n------\n\n".join(
            phrases
        )
        return [
            {"role": "system", "content": INPUT_GUIDE},
            *self._build_history(payload),
            {"role": "user", "content": f"Pergunta: {payload.question}"},
            {"role": "system", "content": f"Trechos: \n\n------\n\n {knowledge}"},
        ]

    def _build_history(self, payload: PayloadQuestionOpenIA) -> list[ChatMessage]:
        return [
            {"role": "user" if item.is_user else "assistant", "content": item.text}
            for item in payload.chat_historic
        ]

    def _parse_moderation(self, raw_answer: str) -> ModerationResult:
        data = self._load_json_object(raw_answer, "Moderation")
        return ModerationResult(
            insult=bool(data.get("insult", False)),
            insult_text=str(data.get("insult_text", "")),
            category=str(data.get("categoria") or "").strip(),
        )

    def _load_json_object(self, raw_answer: str, operation: str) -> dict[str, Any]:
        """Parse the model answer as a JSON object or raise :class:`OpenIaException`."""
        try:
            data = json.loads(self._strip_code_fence(raw_answer))
        except (json.JSONDecodeError, TypeError) as error:
            logger.error("%s response was not valid JSON", operation)
            raise OpenIaException(f"Invalid {operation.lower()} response") from error
        if not isinstance(data, dict):
            logger.error("%s response was not a JSON object", operation)
            raise OpenIaException(f"Invalid {operation.lower()} response")
        return data

    @staticmethod
    def _build_category_rule(categories: list[str]) -> str:
        if not categories:
            return _CATEGORY_RULE_WITHOUT_LIST
        return _CATEGORY_RULE_WITH_LIST.format(categories="\n".join(categories))

    @staticmethod
    def _strip_code_fence(raw_answer: str) -> str:
        text = raw_answer.strip()
        if not text.startswith("```"):
            return text
        without_fence = text.strip("`")
        if without_fence.startswith("json"):
            without_fence = without_fence[len("json") :]
        return without_fence.strip()
