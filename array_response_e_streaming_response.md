# Respostas em array e envio com StreamingResponse
from langchain_text_splitters import json, python

## Contexto
A aplicação atual recebe uma unica resposta do modelo do modelo de LLM num única string.
e essa única mensagem é enviada para o cliente.


## Tarefa

### Respostas da LLM em formato JSON
> - O prompt de envio para a LLM já foi editado e a LLM irá responder com um array de respostas semelhante a esse:
```json
{
    "respostas":
    [
        "resposta 1",
        "resposta 2",
        "resposta 3",
        "resposta 4"
    ]
}
```

- Você deve tratar a resposta da LLM que vira em formato de json com array de respostas
- Você deve gravar no redis com esse json
- Você deve utilizar o mesmo json para gerar novos embeddings para cache semantico


### Resposta para cliente em formato de StreamingResponse
- Você deve enviar a resposta para o cliente em formato de StreamingResponse, enviando cada item do array de respostas separadamente,
para que o cliente possa ir recebendo as respostas em tempo real. Como se fosse um verdadeiro chat
Exemplo de código:
```python
    return StreamingResponse(
        service.search(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

    async def service.search(..):
        ...
        ...
        yield f"data: {json.dumps(result)}\n\n"
```
- Para cada resposta, espere 0.5 segundos para responder a outra resposta. Deixe esse valor configuravel numa constante


## Critérios de aceitação
- Atualize os teste unitário para validar o novo fluxo



