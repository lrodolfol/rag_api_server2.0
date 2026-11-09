"""OpenAI service result models.

These model the typed outputs returned by :class:`OpenAIService`. They stay in
the infrastructure layer because they describe the provider integration's
response contract rather than a core domain concept.
"""

from pydantic import BaseModel, Field


class ModerationResult(BaseModel):
    """Outcome of moderating a piece of client-provided content.

    ``insult`` flags whether inappropriate content was detected and
    ``insult_text`` carries the offending excerpt (empty when nothing was
    flagged). The tech spec's raw example used the ``insult`` key twice; a
    distinct ``insult_text`` field is used here so the contract is valid JSON.
    ``category`` is the category name chosen or suggested by the LLM (``""``
    when none was returned; the fallback is applied by the categories service).
    """

    insult: bool
    insult_text: str = Field(default="")
    category: str = Field(default="")
