"""Unit tests for the domain exceptions."""

import pytest

from app.domain import (
    DomainError,
    InappropriateContentError,
    OpenIaException,
    RateLimitError,
)


@pytest.mark.parametrize(
    "exception_type",
    [OpenIaException, InappropriateContentError, RateLimitError],
)
def test_should_be_a_domain_error(exception_type: type[DomainError]) -> None:
    # Act
    error = exception_type("boundary-safe message")

    # Assert
    assert isinstance(error, DomainError)
    assert str(error) == "boundary-safe message"


def test_should_be_raisable_and_catchable_as_domain_error() -> None:
    # Act / Assert
    with pytest.raises(DomainError):
        raise OpenIaException("No choices returned from OpenAI API")
