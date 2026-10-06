"""Integration tests: realistic registration text flowing through the real
LangChain splitter, end to end (normalisation + chunking)."""

from app.application.text_processing import CHUNK_SIZE, generate_chunks

REGISTRATION_TEXT = """Padaria e Confeitaria Pão Quente



Horário de funcionamento: Seg a Sex: 08h ~ 19h

Formas de pagamento: dinheiro, pix e cartão de crédito

Estacionamento próprio


Site: www.exemplo.com.br
Categoria: economico
Delivery: Sim

Entrega gratuita em domicílio
"""


def test_should_chunk_realistic_registration_text() -> None:
    # Act
    chunks = generate_chunks(REGISTRATION_TEXT)

    # Assert
    assert chunks  # produced at least one chunk
    assert all(chunk.strip() for chunk in chunks)  # no empty chunk
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)


def test_should_drop_blank_lines_from_registration_text() -> None:
    # Act
    chunks = generate_chunks(REGISTRATION_TEXT)
    joined = "\n".join(chunks)

    # Assert
    assert "\n\n" not in joined  # blank lines were removed during normalisation
    assert "Delivery: Sim" in joined
    assert "Entrega gratuita em domicílio" in joined


def test_should_preserve_content_across_chunks() -> None:
    # Act
    chunks = generate_chunks(REGISTRATION_TEXT)

    # Assert
    assert any("Padaria e Confeitaria" in chunk for chunk in chunks)
    assert any("Formas de pagamento" in chunk for chunk in chunks)
