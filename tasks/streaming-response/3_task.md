# Tarefa 3.0: `SearchService` com resposta em array e caches em JSON

<critical>Ler os arquivos `array_response_e_streaming_response.md` (raiz), `tasks/streaming-response/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Esta tarefa leva o `ChatAnswer` por todo o pipeline de busca:

- o cache exato (Redis) e o cache semântico (PostgreSQL) passam a gravar e ler o JSON;
- o threshold semântico mescla os arrays dos matches aceitos;
- o histórico grava os itens unidos em texto;
- `SearchService.search` passa a devolver a **lista de mensagens** que serão enviadas ao cliente:
  a introdução seguida dos itens, ou uma mensagem de "não encontrado".

As rotas ainda devolvem `ApiResponse` ao final desta tarefa. Para isso, elas unem a lista com
`"\n\n"` como adaptação temporária, e a tarefa 4.0 troca essa união pelo streaming.

Depende das tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (o serviço de aplicação coordena; os repositórios continuam guardando `str`)
- `.claude/code_patterns/python-conventions.md` (tipagem, métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha de Redis ou PostgreSQL continua sendo miss)
- `.claude/code_patterns/security.md` (logs sem pergunta, resposta ou embedding)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `app/application/search/service.py`:
  - `search(...) -> list[str]`: devolve as mensagens finais.
    - Com itens: `[choice(_ANSWER_MESSAGES), *answer.respostas]`.
    - Sem itens: `[choice(_NOT_FOUND_MESSAGES)]`.
  - `_get_cached_answer`: converte o valor do Redis com `ChatAnswer.from_json`. Se a conversão
    falhar, loga um warning e trata como miss, sem quebrar a requisição;
  - `threshold_evaluate(matches) -> ChatAnswer | None`: converte o `response` de cada match aceito
    e usa `ChatAnswer.merge`. Um `response` inválido é ignorado com um warning. Se nenhum item for
    aceito, retorna `None`;
  - `_answer_from_semantic_cache`: grava no Redis o JSON mesclado (`to_json()`);
  - `_store_answer`: grava `answer.to_json()` no Redis e no cache semântico, só quando
    `is_cacheable_answer` é verdadeiro;
  - `_run_pipeline`: remove a adaptação `.as_text()` da tarefa 2.0 e retorna `ChatAnswer`;
  - `_persist_turn`: grava `answer.as_text()` como mensagem do assistente, e só quando houver itens;
  - atualizar a docstring do módulo com o novo fluxo.
- `app/application/cache/semantic_cache_service.py`: `store` recebe um `ChatAnswer` e grava
  `to_json()` em `SemanticCacheEntry.response`. O embedding continua sendo o da pergunta.
- `app/application/cache/answer_policy.py`: remove o suporte a `str` deixado na tarefa 1.0.
- **NÃO alterar** os repositórios `RedisAnswerCacheRepository` e `PostgresSemanticCacheRepository`.
  Eles continuam guardando `str`, que agora contém o JSON.
- Rotas `app/api/routes/chat.py` e `app/api/routes/whatsapp.py`: adaptação temporária
  `message="\n\n".join(messages)`, substituída na tarefa 4.0.
</requirements>

## Subtarefas

- [x] 3.1 Fazer o cache exato ler e gravar `ChatAnswer` em JSON.
- [x] 3.2 Fazer `threshold_evaluate` mesclar os arrays dos matches aceitos.
- [x] 3.3 Fazer o `SemanticCacheService.store` receber `ChatAnswer` e gravar o JSON.
- [x] 3.4 Fazer o histórico gravar os itens unidos em texto.
- [x] 3.5 Fazer `search` devolver `list[str]` (introdução e itens, ou "não encontrado").
- [x] 3.6 Aplicar a adaptação temporária nas rotas.
- [x] 3.7 Atualizar os testes unitários e de integração.
- [x] 3.8 Rodar os testes, o lint e o type checking.

## Detalhes de Implementação

As regras estão em `tasks/streaming-response/tasks.md`, nos itens "Cache exato", "Cache semântico",
"Vários matches semânticos", "Histórico" e "Mensagens enviadas ao cliente". O fluxo de hit/miss
continua o mesmo descrito em `tasks/semantic-cache-threshold/tasks.md`; muda só o formato do valor.

Pontos de atenção:

- O `SIMILARITY_THRESHOLD` atual da classe **não** deve ser alterado.
- Nos testes, controle `random.choice` com `monkeypatch` para deixar a introdução determinística.

## Critérios de Sucesso

- Um miss completo grava o mesmo JSON no Redis e no PostgreSQL e grava o texto unido no histórico.
- Um hit exato devolve `[intro, *itens]` sem chamar embedding, cache semântico nem LLM.
- Um hit semântico com 2 matches aceitos devolve os itens mesclados, sem duplicados, e grava o JSON
  mesclado no Redis.
- Um `ChatAnswer` vazio devolve uma única mensagem de "não encontrado" e não grava em cache.
- Um valor corrompido no Redis ou no cache semântico é tratado como miss, com um warning.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/search/test_search_service.py`: hit exato, hit semântico (com mesclagem e
    deduplicação), miss com RAG, resposta vazia, valor corrompido no cache e conteúdo gravado no
    histórico;
  - `tests/unit/cache/test_semantic_cache_service.py`: `store` com `ChatAnswer` (JSON gravado) e
    com `ChatAnswer` vazio (não grava).
- [x] Testes de integração:
  - `tests/integration/redis/test_answer_cache_integration.py`: ida e volta do JSON;
  - `tests/integration/postgres/test_semantic_cache_integration.py`: `response` gravado em JSON;
  - `tests/integration/api/test_search_api.py`: atualizar os cenários do pipeline (`_Pipeline`) para
    respostas em JSON.
- [x] Testes E2E: rodar `tests/integration/api/test_e2e_flows.py` e ajustar os fluxos que dependem
  da resposta em texto.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/application/cache/semantic_cache_service.py`
- `app/application/cache/answer_policy.py`
- `app/api/routes/chat.py` e `app/api/routes/whatsapp.py` (adaptação temporária)
- `app/infrastructure/redis/answer_cache_repository.py` (somente leitura, não alterar)
- `app/infrastructure/postgres/semantic_cache_repository.py` (somente leitura, não alterar)
- `tests/unit/search/test_search_service.py`
- `tests/unit/cache/test_semantic_cache_service.py`
- `tests/integration/redis/test_answer_cache_integration.py`
- `tests/integration/postgres/test_semantic_cache_integration.py`
- `tests/integration/api/test_search_api.py` e `tests/integration/api/test_e2e_flows.py`
