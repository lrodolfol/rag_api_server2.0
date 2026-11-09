"""Unit tests for :class:`PineconeVectorRepository` using a mocked SDK client."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pinecone import NotFoundException
from pinecone.exceptions import PineconeException
from pydantic import SecretStr

from app.domain import EmbeddingRecord, VectorRepositoryError
from app.infrastructure.config import PineconeConfig
from app.infrastructure.pinecone import (
    SIMILARITY_THRESHOLD,
    PineconeVectorRepository,
    VectorMatch,
)


def _config() -> PineconeConfig:
    return PineconeConfig(
        api_key=SecretStr("test-key"),
        index_name="acha-local-services-dev",
        region="us-east-1",
        environment="development",
        metric="cosine",
        vector_type="dense",
        dimension=1536,
    )


def _repository(client: MagicMock) -> PineconeVectorRepository:
    return PineconeVectorRepository(client=client, config=_config())


def _client_with_index(index: MagicMock, *, has_index: bool = True) -> MagicMock:
    client = MagicMock()
    client.has_index.return_value = has_index
    client.Index.return_value = index
    return client


def _match(
    score: float, text: str = "info", user_code: str = "123", category: str = "alimentacao"
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"id-{score}",
        score=score,
        metadata={"text": text, "user_code": user_code, "category": category},
    )


@pytest.mark.asyncio
async def test_should_create_index_when_missing() -> None:
    # Arrange
    client = _client_with_index(MagicMock(), has_index=False)

    # Act
    await _repository(client).create_index_if_not_exists()

    # Assert
    client.create_index.assert_called_once()
    kwargs = client.create_index.call_args.kwargs
    assert kwargs["name"] == "acha-local-services-dev"
    assert kwargs["dimension"] == 1536
    assert kwargs["metric"] == "cosine"
    assert kwargs["vector_type"] == "dense"
    assert kwargs["spec"].region == "us-east-1"
    assert kwargs["tags"] == {"environment": "development"}


@pytest.mark.asyncio
async def test_should_not_create_index_when_present() -> None:
    # Arrange
    client = _client_with_index(MagicMock(), has_index=True)

    # Act
    await _repository(client).create_index_if_not_exists()

    # Assert
    client.create_index.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_when_creating_index() -> None:
    # Arrange
    client = MagicMock()
    client.has_index.side_effect = PineconeException("provider down")

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).create_index_if_not_exists()


@pytest.mark.asyncio
async def test_should_delete_before_upsert_with_deterministic_ids() -> None:
    # Arrange
    index = MagicMock()
    client = _client_with_index(index)
    embeddings = [
        EmbeddingRecord(text="chunk a", vector=[0.1, 0.2]),
        EmbeddingRecord(text="chunk b", vector=[0.3, 0.4]),
    ]

    # Act
    await _repository(client).upsert_company_vectors(
        "Padaria Central", "123", "alimentacao", embeddings
    )

    # Assert
    assert [call[0] for call in index.method_calls] == ["delete", "upsert"]
    index.delete.assert_called_once_with(filter={"user_code": "123"})
    vectors = index.upsert.call_args.kwargs["vectors"]
    assert vectors[0][0] == "PadariaCentral-123-0"
    assert vectors[1][0] == "PadariaCentral-123-1"
    assert vectors[0][1] == [0.1, 0.2]
    assert vectors[0][2] == {"text": "chunk a", "user_code": "123", "category": "alimentacao"}
    assert vectors[1][2] == {"text": "chunk b", "user_code": "123", "category": "alimentacao"}


@pytest.mark.asyncio
async def test_should_skip_upsert_when_no_embeddings() -> None:
    # Arrange
    index = MagicMock()
    client = _client_with_index(index)

    # Act
    await _repository(client).upsert_company_vectors("Padaria", "123", "alimentacao", [])

    # Assert
    client.Index.assert_not_called()
    index.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_upsert() -> None:
    # Arrange
    index = MagicMock()
    index.delete.side_effect = PineconeException("provider down")
    client = _client_with_index(index)
    embeddings = [EmbeddingRecord(text="chunk", vector=[0.1])]

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).upsert_company_vectors("Padaria", "123", "alimentacao", embeddings)


@pytest.mark.asyncio
async def test_should_delete_vectors_by_user_code() -> None:
    # Arrange
    index = MagicMock()
    client = _client_with_index(index)

    # Act
    await _repository(client).delete_by_user_code("987")

    # Assert
    index.delete.assert_called_once_with(filter={"user_code": "987"})


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_delete() -> None:
    # Arrange
    index = MagicMock()
    index.delete.side_effect = PineconeException("provider down")
    client = _client_with_index(index)

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).delete_by_user_code("987")


@pytest.mark.asyncio
async def test_should_ignore_not_found_on_delete() -> None:
    # Arrange
    index = MagicMock()
    index.delete.side_effect = NotFoundException(status=404, reason="Not Found")
    client = _client_with_index(index)

    # Act
    await _repository(client).delete_by_user_code("987")

    # Assert
    index.delete.assert_called_once_with(filter={"user_code": "987"})


@pytest.mark.asyncio
async def test_should_report_vectors_exist_when_filtered_query_has_match() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[_match(0.01)])
    client = _client_with_index(index)

    # Act
    found = await _repository(client).has_vectors_for_user_code("987")

    # Assert
    assert found is True


@pytest.mark.asyncio
async def test_should_report_no_vectors_when_filtered_query_is_empty() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[])
    client = _client_with_index(index)

    # Act
    found = await _repository(client).has_vectors_for_user_code("987")

    # Assert
    assert found is False


@pytest.mark.asyncio
async def test_should_check_vectors_with_user_code_filter_and_configured_dimension() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[])
    client = _client_with_index(index)

    # Act
    await _repository(client).has_vectors_for_user_code("987")

    # Assert
    kwargs = index.query.call_args.kwargs
    assert kwargs["filter"] == {"user_code": "987"}
    assert kwargs["top_k"] == 1
    assert len(kwargs["vector"]) == 1536
    assert any(value != 0 for value in kwargs["vector"])


@pytest.mark.asyncio
async def test_should_report_no_vectors_when_index_not_found() -> None:
    # Arrange
    index = MagicMock()
    index.query.side_effect = NotFoundException(status=404, reason="Not Found")
    client = _client_with_index(index)

    # Act
    found = await _repository(client).has_vectors_for_user_code("987")

    # Assert
    assert found is False


@pytest.mark.asyncio
async def test_should_wrap_provider_error_when_checking_vectors() -> None:
    # Arrange
    index = MagicMock()
    index.query.side_effect = PineconeException("provider down")
    client = _client_with_index(index)

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).has_vectors_for_user_code("987")


@pytest.mark.asyncio
async def test_should_return_only_matches_above_threshold() -> None:
    # Arrange
    below = SIMILARITY_THRESHOLD - 0.01
    above = SIMILARITY_THRESHOLD + 0.01
    index = MagicMock()
    index.query.return_value = SimpleNamespace(
        matches=[_match(0.99), _match(below), _match(SIMILARITY_THRESHOLD), _match(above)]
    )
    client = _client_with_index(index)

    # Act
    results = await _repository(client).query([0.1, 0.2], top_k=4)

    # Assert
    assert [match.score for match in results] == [0.99, above]
    index.query.assert_called_once_with(
        vector=[0.1, 0.2], top_k=4, include_metadata=True
    )


@pytest.mark.asyncio
async def test_should_map_metadata_into_vector_match() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(
        matches=[_match(0.97, text="padaria central", user_code="123")]
    )
    client = _client_with_index(index)

    # Act
    results = await _repository(client).query([0.1])

    # Assert
    assert results == [
        VectorMatch(
            id="id-0.97",
            score=0.97,
            text="padaria central",
            user_code="123",
            category="alimentacao",
        )
    ]


@pytest.mark.asyncio
async def test_should_return_empty_for_blank_embedding() -> None:
    # Arrange
    client = MagicMock()

    # Act
    results = await _repository(client).query([])

    # Assert
    assert results == []
    client.Index.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_query() -> None:
    # Arrange
    index = MagicMock()
    index.query.side_effect = PineconeException("provider down")
    client = _client_with_index(index)

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).query([0.1, 0.2])


@pytest.mark.asyncio
async def test_should_filter_query_by_category_slug() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[_match(0.95)])
    client = _client_with_index(index)

    # Act
    results = await _repository(client).query([0.1, 0.2], category_slug="alimentacao")

    # Assert
    index.query.assert_called_once_with(
        vector=[0.1, 0.2],
        top_k=5,
        include_metadata=True,
        filter={"category": {"$eq": "alimentacao"}},
    )
    assert results[0].category == "alimentacao"


@pytest.mark.asyncio
@pytest.mark.parametrize("category_slug", [None, ""])
async def test_should_query_without_filter_when_no_category(
    category_slug: str | None,
) -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[])
    client = _client_with_index(index)

    # Act
    await _repository(client).query([0.1, 0.2], category_slug=category_slug)

    # Assert
    assert "filter" not in index.query.call_args.kwargs


@pytest.mark.asyncio
async def test_should_map_missing_category_metadata_to_empty_string() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(
        matches=[SimpleNamespace(id="v1", score=0.9, metadata={"text": "a", "user_code": "1"})]
    )
    client = _client_with_index(index)

    # Act
    results = await _repository(client).query([0.1])

    # Assert
    assert results[0].category == ""


@pytest.mark.asyncio
async def test_should_return_category_of_the_client_vectors() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[_match(0.01, category="saude")])
    client = _client_with_index(index)

    # Act
    category = await _repository(client).get_category_by_user_code("987")

    # Assert
    assert category == "saude"
    kwargs = index.query.call_args.kwargs
    assert kwargs["filter"] == {"user_code": "987"}
    assert kwargs["top_k"] == 1
    assert kwargs["include_metadata"] is True
    assert len(kwargs["vector"]) == 1536
    assert any(value != 0 for value in kwargs["vector"])


@pytest.mark.asyncio
async def test_should_return_no_category_when_client_has_no_vectors() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[])
    client = _client_with_index(index)

    # Act / Assert
    assert await _repository(client).get_category_by_user_code("987") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [{"text": "a", "user_code": "987"}, {"text": "a", "user_code": "987", "category": ""}, None],
)
async def test_should_return_no_category_for_legacy_vectors(metadata: dict | None) -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(
        matches=[SimpleNamespace(id="v1", score=0.01, metadata=metadata)]
    )
    client = _client_with_index(index)

    # Act / Assert
    assert await _repository(client).get_category_by_user_code("987") is None


@pytest.mark.asyncio
async def test_should_return_no_category_when_index_not_found() -> None:
    # Arrange
    index = MagicMock()
    index.query.side_effect = NotFoundException(status=404, reason="Not Found")
    client = _client_with_index(index)

    # Act / Assert
    assert await _repository(client).get_category_by_user_code("987") is None


@pytest.mark.asyncio
async def test_should_wrap_provider_error_when_reading_category() -> None:
    # Arrange
    index = MagicMock()
    index.query.side_effect = PineconeException("provider down")
    client = _client_with_index(index)

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await _repository(client).get_category_by_user_code("987")


@pytest.mark.asyncio
async def test_should_check_vectors_without_metadata() -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[])
    client = _client_with_index(index)

    # Act
    await _repository(client).has_vectors_for_user_code("987")

    # Assert
    assert index.query.call_args.kwargs["include_metadata"] is False


@pytest.mark.asyncio
async def test_should_log_category_filter_but_never_user_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    index = MagicMock()
    index.query.return_value = SimpleNamespace(matches=[_match(0.01, user_code="secret-987")])
    client = _client_with_index(index)
    repository = _repository(client)

    # Act
    with caplog.at_level(logging.INFO):
        await repository.query([0.1], category_slug="alimentacao")
        await repository.get_category_by_user_code("secret-987")

    # Assert
    assert "category_filter='alimentacao'" in caplog.text
    assert "secret-987" not in caplog.text
