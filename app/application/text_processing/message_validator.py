"""Short-message detection for incoming chat messages.

Identifies messages that carry no useful content (``"..."``, ``"1234"``,
``"i"``) using only local string inspection, so they can be answered without
calling the language model. Only Unicode alphabetic characters count as
letters (accented ones included); whitespace, digits, punctuation, symbols and
emojis are ignored.
"""

from typing import Final

MIN_MESSAGE_LETTERS: Final[int] = 2


def is_short_message(message: str) -> bool:
    """Return ``True`` when ``message`` has fewer than ``MIN_MESSAGE_LETTERS`` letters."""
    letter_count = sum(1 for char in message if char.isalpha())
    return letter_count < MIN_MESSAGE_LETTERS
