"""Unit tests for text normalisation and deterministic chunking."""

from app.application.text_processing import (
    CHUNK_SIZE,
    generate_chunks,
    normalize_text,
)


def test_should_remove_blank_lines_and_trim_each_line() -> None:
    # Arrange
    text = "  linha 1  \n\n\n   \n  linha 2\n"

    # Act
    result = normalize_text(text)

    # Assert
    assert result == "linha 1\nlinha 2"


def test_should_return_empty_string_for_only_blank_lines() -> None:
    # Arrange
    text = "\n   \n\t\n"

    # Act
    result = normalize_text(text)

    # Assert
    assert result == ""


def test_should_return_empty_list_for_blank_input() -> None:
    # Arrange
    text = "   \n\n  "

    # Act
    chunks = generate_chunks(text)

    # Assert
    assert chunks == []


def test_should_return_single_chunk_for_short_text() -> None:
    # Arrange
    text = "Padaria do Centro. Abre de segunda a sexta."

    # Act
    chunks = generate_chunks(text)

    # Assert
    assert chunks == ["Padaria do Centro. Abre de segunda a sexta."]


def test_should_produce_typed_list_of_strings() -> None:
    # Arrange
    text = "conteudo de exemplo do cadastro"

    # Act
    chunks = generate_chunks(text)

    # Assert
    assert isinstance(chunks, list)
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_should_not_return_empty_chunks() -> None:
    # Arrange
    text = "linha 1\n\n\nlinha 2\n\n\nlinha 3"

    # Act
    chunks = generate_chunks(text)

    # Assert
    assert chunks
    assert all(chunk.strip() for chunk in chunks)


def test_should_split_long_text_into_multiple_chunks() -> None:
    # Arrange
    sentence = "Este estabelecimento oferece diversos servicos de qualidade. "
    text = sentence * 60  # well beyond CHUNK_SIZE characters

    # Act
    chunks = generate_chunks(text)

    # Assert
    assert len(chunks) > 1
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)


def test_should_be_deterministic_for_same_input() -> None:
    # Arrange
    text = "Restaurante Sabor. " * 80

    # Act
    first = generate_chunks(text)
    second = generate_chunks(text)

    # Assert
    assert first == second
