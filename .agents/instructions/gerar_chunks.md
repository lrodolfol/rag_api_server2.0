## Como gerar chunks das informações do cliente antes de gerar os embeddings

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter


def generate_chunks(texto: str): #colocar tipo de retorno
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,       # tamanho do chunk (em caracteres)
        chunk_overlap=100,     # sobreposição entre chunks
        separators=["\n\n", "\n", ".", " ", ""]  # tentará quebrar nessa ordem
    )

    chunks = splitter.split_text(texto)

    return chunks
```