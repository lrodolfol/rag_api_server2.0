# Tarefa 4.0: Cache semântico no fluxo de busca e injeção de dependências

<critical>Ler os arquivos `../../.mine/cache_semantico.md` (raiz), `tasks/semantic-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Liga o cache semântico ao fluxo de busca. Um serviço de aplicação intermediário
(`SemanticCacheService`) esconde do `SearchService` os detalhes do registro (uuid, data,
serialização) e do banco. O `SearchService` passa a: consultar o cache semântico após o miss
exato; em hit semântico, devolver a resposta, gravar o histórico e popular o Redis; em miss
semântico, seguir o RAG e gravar a resposta no Redis e no PostgreSQL.

Depende das tarefas 1.0, 2.0 e 3.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (aplicação depende de serviço intermediário, não de SQL)
- `.claude/code_patterns/python-conventions.md` (async, tipagem, métodos < 30 linhas, clean code)
- `.claude/code_patterns/error-handling.md` (falhas do cache não derrubam a requisição)
- `.claude/code_patterns/security.md` (sem pergunta/resposta nos logs)
- `.claude/code_patterns/api.md` (contrato das rotas permanece igual)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo `SemanticCacheService` em `app/application/cache/semantic_cache_service.py`
  (exportado em `app/application/cache/__init__.py`), recebendo o
  `PostgresSemanticCacheRepository`:
  - `async find_answer(fingerprint: CacheFingerprint, embedding: list[float]) -> str | None`:
    devolve a resposta do `best_match` (primeiro resultado) ou `None` em miss.
    **Sem limiar de similaridade.**
  - `async store(fingerprint, question, answer, embedding) -> None`: monta o
    `SemanticCacheEntry` (`uuid4()`, `created_at` = agora) e grava. Não grava respostas não
    cacheáveis.
- Regra "resposta cacheável" (não vazia, ignorando espaços) em **um único lugar**, compartilhada
  pelo Redis e pelo cache semântico — mover o `_is_cacheable` atual para uma função pura
  reutilizável (ex.: em `app/application/cache/`), sem duplicar.
- `SearchService` recebe `semantic_cache: SemanticCacheService` e implementa o fluxo:
  1. hit exato → histórico + retorno (**sem** embedding e **sem** consultar o cache semântico);
  2. miss exato → gera o embedding (tarefa 3.0) → `semantic_cache.find_answer`;
  3. hit semântico → histórico + `answer_cache.set(cache_key, resposta)` + retorno (sem RAG/LLM);
  4. miss semântico → RAG + LLM → grava no Redis e (`semantic_cache.store`) no PostgreSQL,
     somente se cacheável → histórico → retorno.
- A gravação no PostgreSQL acontece **somente após a resposta da LLM** (nunca no hit semântico).
- Logs de hit/miss semântico com o prefixo de 8 caracteres da `cache_key`; nunca pergunta/resposta.
- `app/api/dependencies.py`: provider `@lru_cache` para o `PostgresSemanticCacheRepository`
  (com `config.postgres` e `config.semantic_cache`) e para o `SemanticCacheService`; injetar no
  `get_search_service`.
- Nenhuma mudança no contrato das rotas.
- Atualizar a docstring do módulo `app/application/search/service.py`.
- Todos os métodos abaixo de 30 linhas (extrair helpers, ex.: `_answer_from_semantic_cache`,
  `_store_answer`).
</requirements>

## Subtarefas

- [x] 4.1 Extrair a regra "resposta cacheável" para função pura reutilizável.
- [x] 4.2 Criar `SemanticCacheService` (`find_answer` e `store`) e exportá-lo.
- [x] 4.3 Integrar o cache semântico no `SearchService` (hit e miss semântico).
- [x] 4.4 Gravação no Redis e no PostgreSQL após a resposta da LLM.
- [x] 4.5 Injeção de dependências em `app/api/dependencies.py`.
- [x] 4.6 Atualizar fixtures/overrides de testes existentes que constroem o `SearchService`.
- [x] 4.7 Testes de unidade.
- [x] 4.8 Testes de integração e E2E da API com mocks.
- [x] 4.9 Rodar a suíte completa (`python -m pytest` no `.venv`), lint e type check.

## Detalhes de Implementação

- Fluxo completo, regras de hit/miss e critérios de aceitação: `../../.mine/cache_semantico.md`, seções 1, 2, 4
  e "Critérios de aceitação".
- Padrões a seguir: `SearchService._store_if_cacheable` (gravação condicional) e os providers
  `_answer_cache_repository` / `get_search_service` em `app/api/dependencies.py`.

## Critérios de Sucesso

- Hit exato não consulta o cache semântico nem gera embedding.
- Hit semântico não chama Pinecone nem LLM, grava histórico e popula o Redis com a chave da pergunta atual.
- Miss semântico executa o RAG e grava no Redis e no PostgreSQL, uma vez, após a LLM.
- Respostas vazias (ou só com espaços) não vão para nenhum dos caches.
- Falha do PostgreSQL resulta no fluxo normal de RAG e a resposta chega ao usuário.
- O embedding é gerado no máximo uma vez por requisição.
- Toda a suíte de testes passa.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/cache/test_semantic_cache_service.py`:
    - `find_answer` devolve a resposta do primeiro resultado; `None` quando a lista é vazia.
    - `store` monta o `SemanticCacheEntry` com uuid, `created_at`, fingerprint, pergunta original,
      resposta e embedding.
    - `store` não chama o repositório para resposta vazia ou só com espaços.
  - `tests/unit/search/test_search_service.py`:
    - Hit exato: cache semântico e embedding não são chamados.
    - Hit semântico: retorna a resposta armazenada; Pinecone e LLM não são chamados; histórico
      gravado; `answer_cache.set` chamado com a `cache_key` atual; `semantic_cache.store` não chamado.
    - Miss semântico: RAG + LLM; `answer_cache.set` e `semantic_cache.store` chamados com o mesmo
      embedding gerado.
    - Resposta não cacheável: nenhum dos caches gravado.
    - Embedding gerado uma única vez em todos os cenários de miss exato.
- [x] Testes de integração (`tests/integration/api/test_search_api.py`):
  - Endpoints de chat e WhatsApp com Redis (`fakeredis`), PostgreSQL, OpenAI e Pinecone mockados
    cobrindo hit exato, hit semântico, miss semântico e falha do PostgreSQL (tratada como miss).
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`):
  - Pergunta 1 (miss total, grava nos dois caches) → pergunta semelhante (hit semântico, popula o
    Redis) → mesma pergunta 2 de novo (hit exato, sem consultar o PostgreSQL).

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/cache/semantic_cache_service.py` (novo)
- `app/application/cache/__init__.py`
- `app/application/search/service.py`
- `app/api/dependencies.py`
- `app/infrastructure/postgres/semantic_cache_repository.py` (apenas leitura)
- `tests/unit/cache/test_semantic_cache_service.py` (novo)
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
