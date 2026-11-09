# Tarefa 2.0: Integração no `SearchService` e documentação

<critical>Ler os arquivos `../../meus_prompts/identificar_mensagem_curta.md` (raiz), `tasks/mensagem-curta/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Com o detector da tarefa 1.0 pronto, esta tarefa faz o `SearchService` responder às mensagens
curtas **logo no início** do fluxo, sem acessar cache, histórico, Pinecone ou OpenAI. O cliente
recebe uma única mensagem aleatória de `_INVALID_MESSAGE_RESPONSES`, pelo mesmo stream SSE das rotas
`/chat` e `/whatsapp`.

A tarefa também atualiza a documentação que descreve o fluxo de busca.

**Depende de:** tarefa 1.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (rotas finas; a regra fica no serviço de aplicação)
- `.claude/code_patterns/python-conventions.md` (tipagem, constantes `Final`, métodos com menos de 30 linhas)
- `.claude/code_patterns/api.md` (o contrato SSE e o envelope de erro não mudam)
- `.claude/code_patterns/security.md` (não registrar o conteúdo da mensagem em logs)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Em `app/application/search/service.py`:
  - adicionar a constante `_INVALID_MESSAGE_RESPONSES: Final[tuple[str, ...]]` com **exatamente**
    os 15 textos de `identificar_mensagem_curta.md`, ao lado de `_NOT_FOUND_MESSAGES` e
    `_ANSWER_MESSAGES`;
  - no início de `search()`, chamar `is_short_message(question)`. Se a mensagem for curta,
    registrar um log `info` com o canal (sem o conteúdo) e retornar `[choice(_INVALID_MESSAGE_RESPONSES)]`;
  - nesse caso, **não** chamar `build_fingerprint`, o cache exato, o embedding, o cache semântico,
    o histórico (leitura ou gravação), o Pinecone nem a OpenAI;
  - manter `search()` com menos de 30 linhas. Se precisar, extrair um método privado pequeno,
    como `_short_message_reply`;
  - atualizar a docstring do módulo, incluindo o novo primeiro passo do fluxo.
- As rotas `app/api/routes/chat.py` e `app/api/routes/whatsapp.py` **não** devem precisar de
  mudança. O rate limit do `/chat` continua sendo aplicado antes do serviço.
- Não mudar os payloads, o formato SSE, `sse_response` nem os contratos públicos.
- Atualizar a documentação de funcionalidades:
  - `tasks/techspec.md`, itens 2.5 e 3.6: descrever que uma mensagem curta, sem LLM e com menos de
    2 letras, recebe uma mensagem aleatória de `_INVALID_MESSAGE_RESPONSES` e não vai para o
    histórico nem para os caches;
  - marcar as tarefas concluídas em `tasks/mensagem-curta/tasks.md`.
</requirements>

## Subtarefas

- [x] 2.1 Adicionar `_INVALID_MESSAGE_RESPONSES` ao `service.py`.
- [x] 2.2 Adicionar a verificação de mensagem curta no início de `SearchService.search`.
- [x] 2.3 Atualizar a docstring do módulo `service.py`.
- [x] 2.4 Criar os testes unitários do serviço.
- [x] 2.5 Criar os testes de integração das rotas `/chat` e `/whatsapp`.
- [x] 2.6 Atualizar `tasks/techspec.md` (itens 2.5 e 3.6).
- [x] 2.7 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

As regras completas estão em `tasks/mensagem-curta/tasks.md`, na seção "Regras de negócio
decididas", nos itens "Ponto de verificação", "Resposta", "Histórico e caches", "Rate limit" e
"Logs". O retorno curto usa o mesmo tipo de hoje (`list[str]`), então a camada SSE
(`app/api/patterns/streaming.py`) emite um único evento sem nenhuma alteração.

## Critérios de Sucesso

- Para `"..."`, `search()` retorna uma lista com 1 item, e esse item pertence a
  `_INVALID_MESSAGE_RESPONSES`.
- Para uma mensagem curta, os mocks de OpenAI, Pinecone, Redis (histórico e cache) e cache semântico
  **não** são chamados.
- Para uma mensagem válida (por exemplo, `"pizzaria no centro"`), o fluxo atual não muda, e os
  testes existentes de `tests/unit/search/test_search_service.py` continuam passando sem alteração.
- `POST /chat` e `POST /whatsapp` com uma mensagem curta retornam `200`, `text/event-stream` e
  exatamente um evento `data: {"message": "<texto de _INVALID_MESSAGE_RESPONSES>"}`.
- Nenhum log contém o texto da mensagem recebida.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade: em `tests/unit/search/test_search_service.py`:
  - um teste parametrizado com os exemplos curtos do documento, que verifica o retorno de 1 item de
    `_INVALID_MESSAGE_RESPONSES`;
  - asserções `assert_not_called` / `assert_not_awaited` para OpenAI, Pinecone, histórico, cache
    exato e cache semântico;
  - um caso válido no limite (`"oi"`), que verifica que o fluxo normal continua sendo executado.
- [x] Testes de integração: em `tests/integration/api/test_search_api.py`:
  - `/chat` e `/whatsapp` com uma mensagem curta: status, `media_type`, quantidade de eventos e
    texto pertencente à lista;
  - o rate limit do `/chat` continua contando para mensagens curtas.
- [ ] Testes E2E: em `tests/integration/api/test_e2e_flows.py`, adicionar um cenário de mensagem
  curta seguida de uma mensagem válida do mesmo usuário. O histórico só pode conter o turno da
  mensagem válida.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/application/text_processing/__init__.py` (somente leitura: origem de `is_short_message`)
- `app/api/routes/chat.py` e `app/api/routes/whatsapp.py` (somente leitura: não devem mudar)
- `app/api/patterns/streaming.py` (somente leitura)
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
- `tasks/techspec.md`
- `tasks/mensagem-curta/tasks.md`
