"""Unit tests for the :class:`Category` domain model and the slug rules."""

import pytest
from pydantic import ValidationError

from app.domain import Category, slugify


@pytest.mark.parametrize(
    ("name", "expected_name", "expected_slug"),
    [
        ("Serviços Profissionais", "SERVIÇOS PROFISSIONAIS", "servicos_profissionais"),
        ("ALIMENTAÇÃO", "ALIMENTAÇÃO", "alimentacao"),
        ("CASA E MANUTENÇÃO", "CASA E MANUTENÇÃO", "casa_e_manutencao"),
        ("  saúde  ", "SAÚDE", "saude"),
        ("alimentacao", "ALIMENTACAO", "alimentacao"),
        ("PetShop", "PETSHOP", "petshop"),
    ],
)
def test_should_build_name_and_slug_from_any_spelling(
    name: str, expected_name: str, expected_slug: str
) -> None:
    # Act
    category = Category.from_name(name)

    # Assert
    assert category.name == expected_name
    assert category.slug == expected_slug


@pytest.mark.parametrize(
    ("name", "expected_slug"),
    [
        ("Agropecuária", "agropecuaria"),
        ("SERVIÇOS   PÚBLICOS", "servicos_publicos"),
        ("Bares & Restaurantes", "bares__restaurantes"),
        ("Moda-Praia 2026!", "modapraia_2026"),
        ("já_existe", "ja_existe"),
    ],
)
def test_should_slugify_removing_accents_and_symbols(name: str, expected_slug: str) -> None:
    # Act / Assert
    assert slugify(name) == expected_slug


@pytest.mark.parametrize("name", ["", "   ", "\t\n", "!!!"])
def test_should_reject_name_without_letters_or_digits(name: str) -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        Category.from_name(name)


def test_should_be_immutable() -> None:
    # Arrange
    category = Category.from_name("MODA")

    # Act / Assert
    with pytest.raises(ValidationError):
        category.name = "BELEZA"
