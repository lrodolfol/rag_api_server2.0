# Tarefa 4.0: Rotas `/chat` e `/whatsapp` com `StreamingResponse`

<critical>Ler os arquivos `array_response_e_streaming_response.md` (raiz), `tasks/streaming-response/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

As rotas `/chat` e `/whatsapp` deixam de devolver um `ApiResponse` único. Elas passam a devolver um
`StreamingResponse` (Server-Sent Events) que envia cada mensagem da lista produzida pelo
`SearchService` como um evento separado, com um intervalo configurável entre eles, para o cliente
ver as mensagens chegando como em um chat.

Depende da tarefa 3.0 (`SearchService.search` devolvendo `list[str]`).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/api.md` (rotas finas e contrato HTTP)
- `.claude/code_patterns/architecture.md` (a formatação SSE pertence à camada de API, não ao domínio)
- `.claude/code_patterns/python-conventions.md` (código assíncrono e tipado, métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md` (os erros acontecem antes do stream e continuam com o envelope padrão)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Criar o gerador assíncrono de eventos SSE na camada de API, por exemplo em
  `app/api/patterns/streaming.py`:
  - constante `STREAM_DELAY_SECONDS: Final[float] = 0.5`;
  - `async def stream_messages(messages: list[str]) -> AsyncIterator[str]` emite
    `data: {json.dumps({"message": msg}, ensure_ascii=False)}\n\n` para cada mensagem;
  - usa `await asyncio.sleep(STREAM_DELAY_SECONDS)` **entre** os eventos: não espera antes do
    primeiro nem depois do último;
  - uma função auxiliar monta o `StreamingResponse` com `media_type="text/event-stream"` e os
    headers `Cache-Control: no-cache` e `X-Accel-Buffering: no`, reaproveitada pelas duas rotas.
- `app/api/routes/chat.py` e `app/api/routes/whatsapp.py`:
  - continuam chamando `limiter.check_and_increment` (só no `/chat`) e `await service.search(...)`
    **antes** de criar o `StreamingResponse`, para que os erros continuem passando pelos handlers
    globais com o envelope `ApiResponse`;
  - removem a adaptação temporária da tarefa 3.0 (`"\n\n".join`);
  - removem `response_model=ApiResponse` do decorator e informam na documentação OpenAPI que a
    resposta é `text/event-stream`, por exemplo com `response_class` ou `responses=`;
  - mantêm os logs atuais de recebimento e envio.
- Não alterar `SearchService` nem os handlers globais de erro.
- Não adicionar dependências: usar `fastapi.responses.StreamingResponse`, `asyncio` e `json`.
</requirements>

## Subtarefas

- [x] 4.1 Criar o gerador SSE com a constante `STREAM_DELAY_SECONDS`.
- [x] 4.2 Criar a função auxiliar que monta o `StreamingResponse` com os headers.
- [x] 4.3 Fazer a rota `/chat` devolver o stream, mantendo o rate limit antes do stream.
- [x] 4.4 Fazer a rota `/whatsapp` devolver o stream.
- [x] 4.5 Criar os testes unitários do gerador.
- [x] 4.6 Atualizar os testes de integração e E2E das rotas.
- [x] 4.7 Rodar os testes, o lint e o type checking.

## Detalhes de Implementação

As regras estão em `tasks/streaming-response/tasks.md`, nos itens "Streaming (SSE)" e
"Ordem do fluxo". Veja o exemplo de `StreamingResponse` no documento
`array_response_e_streaming_response.md`.

Pontos de atenção:

- Nos testes unitários, faça o `monkeypatch` de `asyncio.sleep` (ou da constante) para não esperar
  de verdade e para verificar quantas vezes ele é chamado: N mensagens geram N-1 chamadas.
- Nos testes de integração com o `TestClient`, leia o corpo e separe os eventos por `"\n\n"`, ou use
  `client.stream(...)`. Valide o `content-type` `text/event-stream` e os headers.
- O rate limit excedido no `/chat` continua devolvendo 429 com o envelope `ApiResponse`, e não um stream.

## Critérios de Sucesso

- `/chat` e `/whatsapp` respondem 200 com `content-type: text/event-stream` e os dois headers.
- O corpo contém um evento `data: {"message": ...}` por mensagem, na ordem: a introdução e depois os
  itens.
- "Não encontrado" gera exatamente um evento.
- O intervalo entre eventos usa `STREAM_DELAY_SECONDS`, e não há espera antes do primeiro nem depois
  do último evento.
- Rate limit, payload inválido e falha da OpenAI continuam devolvendo o envelope `ApiResponse` com o
  status correto.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (por exemplo `tests/unit/api/test_streaming.py`):
  - formato de cada evento, incluindo caracteres acentuados;
  - quantidade de chamadas ao `sleep` (N-1) e uso da constante;
  - lista com uma mensagem: um evento e nenhum `sleep`.
- [x] Testes de integração (`tests/integration/api/test_search_api.py`):
  - `/whatsapp` e `/chat` devolvem os eventos SSE na ordem certa, com os headers e o content-type;
  - o rate limit do `/chat` continua devolvendo 429 com o envelope padrão;
  - o payload inválido continua devolvendo 422 com o envelope padrão.
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`): ajustar os fluxos para ler as
  respostas em stream.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/api/patterns/streaming.py` (novo)
- `app/api/patterns/response.py` (referência do envelope atual)
- `app/api/routes/chat.py`
- `app/api/routes/whatsapp.py`
- `app/api/errors/handlers.py` (somente leitura)
- `tests/unit/api/` (novo)
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
