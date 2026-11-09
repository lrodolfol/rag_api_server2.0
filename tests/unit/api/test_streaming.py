"""Unit tests for the SSE streaming helpers of the API layer.

``asyncio.sleep`` is replaced with a recording fake, so the tests never wait and
can assert how many pauses happened between events and with which delay.
"""

import json

import pytest

from app.api.patterns import streaming
from app.api.patterns.streaming import (
    STREAM_DELAY_SECONDS,
    format_event,
    sse_response,
    stream_messages,
)


@pytest.fixture
def sleep_calls(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace ``asyncio.sleep`` in the module and record each requested delay."""
    calls: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        calls.append(delay)

    monkeypatch.setattr(streaming.asyncio, "sleep", _fake_sleep)
    return calls


async def _collect(messages: list[str]) -> list[str]:
    return [event async for event in stream_messages(messages)]


def test_should_format_event_as_sse_data_line_with_json_message() -> None:
    # Act
    event = format_event("Padaria Central")

    # Assert
    assert event == 'data: {"message": "Padaria Central"}\n\n'


def test_should_keep_accented_characters_unescaped_in_event() -> None:
    # Act
    event = format_event("Café São João")

    # Assert
    assert event == 'data: {"message": "Café São João"}\n\n'
    assert json.loads(event.removeprefix("data: ")) == {"message": "Café São João"}


def test_should_escape_quotes_and_newlines_through_json() -> None:
    # Act
    event = format_event('Linha "um"\nLinha dois')

    # Assert: the event stays on a single data line.
    assert event.count("\n") == 2
    assert json.loads(event.removeprefix("data: ")) == {"message": 'Linha "um"\nLinha dois'}


@pytest.mark.asyncio
async def test_should_emit_one_event_per_message_in_order(sleep_calls: list[float]) -> None:
    # Arrange
    messages = ["Encontrei para você:", "Padaria Central", "Café São João"]

    # Act
    events = await _collect(messages)

    # Assert
    assert events == [format_event(message) for message in messages]


@pytest.mark.asyncio
async def test_should_sleep_only_between_events_using_constant(
    sleep_calls: list[float],
) -> None:
    # Arrange
    messages = ["a", "b", "c", "d"]

    # Act
    await _collect(messages)

    # Assert: N messages produce N-1 pauses of STREAM_DELAY_SECONDS.
    assert sleep_calls == [STREAM_DELAY_SECONDS] * 3


@pytest.mark.asyncio
async def test_should_not_sleep_before_first_event(sleep_calls: list[float]) -> None:
    # Arrange
    stream = stream_messages(["a", "b"])

    # Act
    first = await anext(stream)

    # Assert
    assert first == format_event("a")
    assert sleep_calls == []


def test_should_define_half_second_stream_delay() -> None:
    assert STREAM_DELAY_SECONDS == 0.5


def test_should_build_streaming_response_with_sse_media_type_and_headers() -> None:
    # Act
    response = sse_response(["a"])

    # Assert
    assert response.media_type == "text/event-stream"
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
