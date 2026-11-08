"""Integration tests: the short-message detector exposed by the public
text-processing package, applied to realistic chat messages."""

from app.application.text_processing import is_short_message


def test_should_flag_content_less_chat_message_through_public_package() -> None:
    # Act / Assert
    assert is_short_message("  ...  ") is True


def test_should_accept_realistic_chat_question_through_public_package() -> None:
    # Act / Assert
    assert is_short_message("Onde encontro uma padaria aberta agora?") is False
