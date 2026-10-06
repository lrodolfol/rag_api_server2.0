"""Text preparation for the embedding pipeline.

Prepares client-submitted text before embeddings are generated:

* normalisation, dropping blank lines (and surrounding whitespace noise);
* deterministic splitting into chunks with LangChain's
  :class:`RecursiveCharacterTextSplitter`.

The splitter parameters come from module constants (never scattered magic
values) following the project's ``gerar_chunks.md`` instruction.
"""

from typing import Final

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE: Final[int] = 900
CHUNK_OVERLAP: Final[int] = 100
CHUNK_SEPARATORS: Final[list[str]] = ["\n\n", "\n", ".", " ", ""]


def normalize_text(text: str) -> str:
    """Remove blank lines and trim whitespace from each remaining line.

    Returns the lines that still hold content, joined by a single newline.
    """
    non_blank_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(non_blank_lines)


def generate_chunks(text: str) -> list[str]:
    """Normalise ``text`` and split it into non-empty chunks.

    Splitting is deterministic for the same input. An empty or blank input
    yields an empty list, and no blank chunk is ever returned.
    """
    normalized_text = normalize_text(text)
    if not normalized_text:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
    )
    chunks = splitter.split_text(normalized_text)
    return [chunk for chunk in chunks if chunk.strip()]
