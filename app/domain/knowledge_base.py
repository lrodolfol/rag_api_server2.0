"""Knowledge base item: a content chunk with its embedding and metadata."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeBaseItem:
    content: str
    embedding: list[float]
    langchain_metadata: dict[str, str] = field(default_factory=dict)
    id: int | None = None
