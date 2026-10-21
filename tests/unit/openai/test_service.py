"""Unit tests for :class:`OpenAIService` using a mocked provider client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import OpenAIError
from pydantic import SecretStr

from app.domain import (
    MessageHistoryItem,
    MessageRole,
    OpenIaException,
    PayloadQuestionOpenIA,
)
from app.infrastructure.config import OpenAIConfig
from app.infrastructure.openai import ModerationResult, OpenAIService


def _config() -> OpenAIConfig:
    return OpenAIConfig(
        api_key=SecretStr("test-key"),
        model_embeddings="text-embedding-ada-002",
        model_chat="gpt-3.5-turbo",
        input_guide="responda com base no contexto",
        pattern_response="Sem resposta disponível",
    )


def _service_with(client: MagicMock) -> OpenAIService:
    return OpenAIService(client=client, config=_config())


def _embedding_response(vector: list[float]) -> SimpleNamespace:
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


def _client_with_response(output_text: str) -> MagicMock:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(output_text=output_text)
    )
    return client


@pytest.mark.asyncio
async def test_should_flag_inappropriate_content() -> None:
    # Arrange
    client = _client_with_response('{"insult": true, "insult_text": "palavrao"}')

    # Act
    result = await _service_with(client).moderate("dados ofensivos")

    # Assert
    assert isinstance(result, ModerationResult)
    assert result.insult is True
    assert result.insult_text == "palavrao"


@pytest.mark.asyncio
async def test_should_not_flag_clean_content() -> None:
    # Arrange
    client = _client_with_response('{"insult": false, "insult_text": ""}')

    # Act
    result = await _service_with(client).moderate("empresa de bolos")

    # Assert
    assert result.insult is False
    assert result.insult_text == ""


@pytest.mark.asyncio
async def test_should_parse_moderation_wrapped_in_code_fence() -> None:
    # Arrange
    client = _client_with_response('```json\n{"insult": false, "insult_text": ""}\n```')

    # Act
    result = await _service_with(client).moderate("empresa")

    # Assert
    assert result.insult is False


@pytest.mark.asyncio
async def test_should_raise_when_moderation_response_is_not_json() -> None:
    # Arrange
    client = _client_with_response("isto nao e json")

    # Act / Assert
    with pytest.raises(OpenIaException):
        await _service_with(client).moderate("empresa")


@pytest.mark.asyncio
async def test_should_generate_embedding_record_per_chunk() -> None:
    # Arrange
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        side_effect=[_embedding_response([0.1, 0.2]), _embedding_response([0.3, 0.4])]
    )

    # Act
    records = await _service_with(client).generate_embeddings_from_chunks(["a", "b"])

    # Assert
    assert [record.text for record in records] == ["a", "b"]
    assert records[0].vector == [0.1, 0.2]
    assert records[1].vector == [0.3, 0.4]


@pytest.mark.asyncio
async def test_should_return_empty_list_for_no_chunks() -> None:
    # Arrange
    client = MagicMock()
    client.embeddings.create = AsyncMock()

    # Act
    records = await _service_with(client).generate_embeddings_from_chunks([])

    # Assert
    assert records == []
    client.embeddings.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_generate_embedding_for_question() -> None:
    # Arrange
    client = MagicMock()
    client.embeddings.create = AsyncMock(return_value=_embedding_response([0.5, 0.6]))

    # Act
    vector = await _service_with(client).generate_embedding_for_question("onde comer?")

    # Assert
    assert vector == [0.5, 0.6]


@pytest.mark.asyncio
async def test_should_return_empty_vector_for_blank_question() -> None:
    # Arrange
    client = MagicMock()
    client.embeddings.create = AsyncMock()

    # Act
    vector = await _service_with(client).generate_embedding_for_question("   ")

    # Assert
    assert vector == []
    client.embeddings.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_generate_chat_answer() -> None:
    # Arrange
    client = _client_with_response("resposta final")
    payload = PayloadQuestionOpenIA(question="onde comer?")

    # Act
    answer = await _service_with(client).generate_chat_answer(payload, ["trecho 1"])

    # Assert
    assert answer == "resposta final"


@pytest.mark.asyncio
async def test_should_build_chat_input_with_guide_history_and_matches() -> None:
    # Arrange
    client = _client_with_response("ok")
    payload = PayloadQuestionOpenIA(
        question="e sobremesa?",
        chat_historic=[
            MessageHistoryItem(role=MessageRole.USER, text="onde comer?"),
            MessageHistoryItem(role=MessageRole.ASSISTANT, text="varios lugares"),
        ],
    )

    # Act
    await _service_with(client).generate_chat_answer(payload, ["doceria central"])

    # Assert
    call = client.responses.create.await_args
    sent = call.kwargs["input"]
    assert sent[0] == {"role": "system", "content": "responda com base no contexto"}
    assert sent[1] == {"role": "user", "content": "onde comer?"}
    assert sent[2] == {"role": "assistant", "content": "varios lugares"}
    assert sent[3] == {"role": "user", "content": "Pergunta: e sobremesa?"}
    assert sent[4]["role"] == "system"
    assert "doceria central" in sent[4]["content"]
    assert call.kwargs["model"] == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_should_return_empty_answer_for_invalid_payload() -> None:
    # Arrange
    client = MagicMock()
    client.responses.create = AsyncMock()
    payload = PayloadQuestionOpenIA(question="   ")

    # Act
    answer = await _service_with(client).generate_chat_answer(payload, [])

    # Assert
    assert answer == ""
    client.responses.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_raise_when_chat_answer_is_empty() -> None:
    # Arrange
    client = _client_with_response("")
    payload = PayloadQuestionOpenIA(question="pergunta")

    # Act / Assert
    with pytest.raises(OpenIaException):
        await _service_with(client).generate_chat_answer(payload, [])


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_embeddings() -> None:
    # Arrange
    client = MagicMock()
    client.embeddings.create = AsyncMock(side_effect=OpenAIError("provider down"))

    # Act / Assert
    with pytest.raises(OpenIaException):
        await _service_with(client).generate_embedding_for_question("pergunta")


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_chat() -> None:
    # Arrange
    client = MagicMock()
    client.responses.create = AsyncMock(side_effect=OpenAIError("provider down"))
    payload = PayloadQuestionOpenIA(question="pergunta")

    # Act / Assert
    with pytest.raises(OpenIaException):
        await _service_with(client).generate_chat_answer(payload, [])
