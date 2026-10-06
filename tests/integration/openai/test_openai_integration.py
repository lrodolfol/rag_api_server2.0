"""Integration tests for the OpenAI service with a fake provider client.

No real OpenAI calls are made: a hand-written fake client returns canned
responses so the full service flow (prompt building, parsing, record creation)
is exercised end to end across its public methods.
"""

import json
from types import SimpleNamespace

import pytest
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.domain import MessageHistoryItem, MessageRole, PayloadQuestionOpenIA
from app.infrastructure.config import OpenAIConfig
from app.infrastructure.openai import OpenAIService, create_openai_client


class _FakeEmbeddings:
    def __init__(self, vector: list[float]) -> None:
        self._vector = vector
        self.inputs: list[str] = []

    async def create(self, *, input: str, model: str) -> SimpleNamespace:
        self.inputs.append(input)
        return SimpleNamespace(data=[SimpleNamespace(embedding=self._vector)])


class _FakeResponses:
    def __init__(self, output_text: str) -> None:
        self._output_text = output_text
        self.calls: list[list[dict[str, str]]] = []

    async def create(self, *, model: str, input: list[dict[str, str]]) -> SimpleNamespace:
        self.calls.append(input)
        return SimpleNamespace(output_text=self._output_text)


class _FakeOpenAIClient:
    def __init__(self, *, vector: list[float], output_text: str) -> None:
        self.embeddings = _FakeEmbeddings(vector)
        self.responses = _FakeResponses(output_text)


def _config() -> OpenAIConfig:
    return OpenAIConfig(
        api_key=SecretStr("integration-key"),
        model_embeddings="emb-model",
        model_chat="chat-model",
        input_guide="guia do assistente",
    )


@pytest.mark.asyncio
async def test_should_flag_insult_through_full_moderation_flow() -> None:
    # Arrange
    raw = json.dumps({"insult": True, "insult_text": "xingamento"})
    client = _FakeOpenAIClient(vector=[], output_text=raw)
    service = OpenAIService(client=client, config=_config())

    # Act
    result = await service.moderate("dados do cliente")

    # Assert
    assert result.insult is True
    assert result.insult_text == "xingamento"


@pytest.mark.asyncio
async def test_should_run_embeddings_and_chat_flow_end_to_end() -> None:
    # Arrange
    client = _FakeOpenAIClient(vector=[0.1, 0.2, 0.3], output_text="resposta final")
    service = OpenAIService(client=client, config=_config())
    payload = PayloadQuestionOpenIA(
        question="onde comer?",
        chat_historic=[MessageHistoryItem(role=MessageRole.USER, text="ola")],
    )

    # Act
    records = await service.generate_embeddings_from_chunks(["chunk a", "chunk b"])
    question_vector = await service.generate_embedding_for_question("pergunta")
    answer = await service.generate_chat_answer(payload, ["trecho relevante"])

    # Assert
    assert [record.text for record in records] == ["chunk a", "chunk b"]
    assert all(record.vector == [0.1, 0.2, 0.3] for record in records)
    assert question_vector == [0.1, 0.2, 0.3]
    assert answer == "resposta final"
    # guide + one history message + question + phrases
    assert len(client.responses.calls[0]) == 4


@pytest.mark.asyncio
async def test_should_build_real_async_client_without_network_call() -> None:
    # Act
    client = create_openai_client(_config(), timeout=5.0)

    # Assert
    assert isinstance(client, AsyncOpenAI)
    assert client.api_key == "integration-key"
    assert client.timeout == 5.0
