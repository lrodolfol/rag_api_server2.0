# Tarefa 4.0: Cache no `SearchService` e injeção de dependências

<critical>Ler os arquivos `../../.mine/implementacao_cahce.md` (raiz), `tasks/cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Ligar o cache ao fluxo de busca compartilhado pelos endpoints WhatsApp e chat online. Antes de
gerar embeddings, o `SearchService` monta a chave (tarefa 2.0) e consulta o repositório
(tarefa 3.0). Hit: devolve a resposta sem chamar OpenAI nem Pinecone, mas grava o histórico.
Miss: segue o fluxo atual e grava a resposta no cache quando ela for cacheável. O contrato dos
endpoints não muda.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (orquestração na camada de aplicação; DI em `app/api/dependencies.py`)
- `.claude/code_patterns/python-conventions.md` (async, tipagem, métodos < 30 linhas — extrair helpers privados)
- `.claude/code_patterns/error-handling.md` (cache nunca quebra a busca)
- `.claude/code_patterns/security.md` (sem pergunta/`user_code` nos logs)
- `.claude/code_patterns/api.md` (o envelope de resposta dos endpoints não muda)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `SearchService.__init__` recebe também `answer_cache: RedisAnswerCacheRepository` e
  `fingerprint_config: FingerPrintConfig`.
- Novo fluxo de `search(channel, user_key, question)`:
  1. Montar a chave com `build_fingerprint` + `build_cache_key`.
  2. `answer_cache.get(key)`. **Hit:** gravar o turno no histórico (`_persist_turn`) e devolver a
     resposta, sem chamar `generate_embedding_for_question`, `vectors.query` nem
     `generate_chat_answer`.
  3. **Miss:** executar o fluxo atual sem alterações (histórico → embeddings → Pinecone → chat →
     histórico).
  4. Depois do miss, gravar no cache **somente** se a resposta não for vazia e for diferente de
     `PATTERN_RESPONSE` (`app/domain/prompts.py`). A comparação deve ignorar espaços nas pontas.
- O histórico continua sendo carregado e usado só no caminho de miss. No hit não é preciso ler o
  histórico; basta gravar o turno.
- `search` deve continuar com menos de 30 linhas: extrair helpers privados
  (ex.: `_cache_key`, `_run_pipeline`, `_store_if_cacheable`).
- Logs: "cache hit" / "cache miss" / "answer cached" / "answer not cacheable", com o canal e o
  prefixo do hash, sem a pergunta.
- `app/api/dependencies.py`:
  - Novo provider `@lru_cache` `_answer_cache_repository()`.
  - Reusar o **mesmo** cliente Redis do histórico: extrair um `@lru_cache _redis_client()` usado
    por `_history_repository()` e `_answer_cache_repository()`, em vez de abrir duas conexões.
  - `get_search_service()` passa `answer_cache` e `get_config().finger_print`.
- Não alterar as rotas (`app/api/routes/chat.py`, `app/api/routes/whatsapp.py`), os payloads nem o
  rate limiter.
- Atualizar todos os pontos que constroem `SearchService` nos testes existentes.
</requirements>

## Subtarefas

- [x] 4.1 Adicionar `answer_cache` e `fingerprint_config` ao construtor do `SearchService`.
- [x] 4.2 Implementar a consulta ao cache e o caminho de hit (com gravação do histórico).
- [x] 4.3 Implementar a regra "é cacheável?" e a gravação depois do miss.
- [x] 4.4 Extrair helpers para manter os métodos com menos de 30 linhas e adicionar os logs.
- [x] 4.5 Atualizar `app/api/dependencies.py` (cliente Redis compartilhado + novo provider).
- [x] 4.6 Ajustar os testes existentes do `SearchService` e da API ao novo construtor.
- [x] 4.7 Testes de unidade.
- [x] 4.8 Testes de integração / E2E.

## Detalhes de Implementação

- Fluxo atual de busca: `tasks/techspec.md`, itens 2 e 3, e `app/application/search/service.py`.
- Regras de hit, escrita, canais compartilhados e falhas: `tasks/cache/tasks.md`, "Regras de
  negócio decididas".
- O repositório já trata `RedisError` (tarefa 3.0). O serviço não precisa de `try/except` próprio
  para o cache.

## Critérios de Sucesso

- Segunda pergunta idêntica (ou equivalente após a normalização), em qualquer canal, é respondida
  sem chamada à OpenAI e ao Pinecone.
- No hit, o histórico do usuário recebe a pergunta e a resposta, igual ao fluxo normal.
- Respostas vazias e `PATTERN_RESPONSE` nunca vão para o cache.
- Com o Redis fora do ar, a busca funciona como antes (sem cache).
- Contrato dos endpoints `/whatsapp` e chat online inalterado; todos os testes que já existiam passam.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/search/test_search_service.py`, com mocks de
  `OpenAIService`, `PineconeVectorRepository`, `RedisHistoryRepository` e `RedisAnswerCacheRepository`):
  - Hit: devolve a resposta do cache; OpenAI e Pinecone **não** são chamados; `append_message`
    chamado para a pergunta e a resposta.
  - Miss: fluxo completo executado; `answer_cache.set` chamado com a chave e a resposta.
  - Miss com resposta vazia → `set` **não** chamado.
  - Miss com `PATTERN_RESPONSE` (inclusive com espaços nas pontas) → `set` **não** chamado.
  - Perguntas equivalentes após a normalização usam a mesma chave.
  - `get` devolvendo `None` por falha do Redis → fluxo normal.
- [x] Testes de integração (`tests/integration/api/test_search_api.py` e/ou
  `tests/integration/api/test_e2e_flows.py`, com `FakeAsyncRedis` e OpenAI/Pinecone mockados via
  `dependency_overrides`):
  - Duas requisições idênticas no chat online → a segunda não chama OpenAI; as duas recebem a mesma resposta.
  - Pergunta feita no WhatsApp e repetida no chat online → hit (cache compartilhado).
  - Chave gravada com o prefixo `rag_answer_cache:` e TTL de ~24h.
  - Histórico do usuário contém os dois turnos depois do hit.
- [x] Testes E2E: cobertos pelos fluxos de API acima.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/api/dependencies.py`
- `app/application/cache/fingerprint.py` (tarefa 2.0)
- `app/infrastructure/redis/answer_cache_repository.py` (tarefa 3.0)
- `app/domain/prompts.py` (`PATTERN_RESPONSE`, apenas leitura)
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
