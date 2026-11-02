# Tarefa 2.0: Repositório do cache semântico no PostgreSQL

<critical>Ler os arquivos `../../.mine/cache_semantico.md` (raiz), `tasks/semantic-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Cria a camada de infraestrutura que conversa com a tabela `rag_response_cache` (já criada no
banco): busca os N registros mais próximos de um embedding, filtrando pelo fingerprint, e grava
novos registros. É o **único** ponto da aplicação que conhece SQL e `psycopg`. Assim como o
`RedisAnswerCacheRepository`, falhas nunca derrubam a requisição.

Depende da tarefa 1.0 (`PostgresConfig` e `SemanticCacheConfig`).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (infraestrutura isolada; domínio sem dependência de banco)
- `.claude/code_patterns/python-conventions.md` (async, tipagem, modelos, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (não engolir exceções em silêncio: logar e devolver miss)
- `.claude/code_patterns/security.md` (SQL 100% parametrizado; sem pergunta/resposta/senha nos logs)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Modelos de domínio em `app/domain/cache.py` (exportados em `app/domain/__init__.py`):
  - `SemanticCacheEntry` (imutável): `id: UUID`, `fingerprint: CacheFingerprint`,
    `input_text: str`, `response: str`, `embedding: list[float]`, `created_at: datetime`.
  - `SemanticCacheMatch` (imutável): `input_text: str`, `response: str`, `distance: float`,
    `similarity: float`.
- Novo pacote `app/infrastructure/postgres/` com:
  - `client.py`: função que abre uma `psycopg.AsyncConnection` a partir de `PostgresConfig`
    (senha via `get_secret_value()`), usada com `async with` — uma conexão por operação.
  - `semantic_cache_repository.py`: classe `PostgresSemanticCacheRepository` recebendo
    `PostgresConfig` e `SemanticCacheConfig`, com:
    - `async find_nearest(embedding: list[float], fingerprint: CacheFingerprint) -> list[SemanticCacheMatch]`
      usando o SQL de `cache_semantico.md` (seção 1.4) com os parâmetros nomeados
      `embedding`, `prompt_version`, `rules_version`, `model_capability`, `limit`
      (`limit` = `semantic_cache.top_k`). Retorna ordenado do mais parecido para o menos.
    - `async save(entry: SemanticCacheEntry) -> None` gravando todas as colunas da tabela.
  - `__init__.py` exportando o repositório e a função de conexão.
- O nome da tabela vem de `semantic_cache.table`. Como identificador não pode ser parâmetro,
  compor com `psycopg.sql.Identifier` (nunca f-string). Todos os **valores** são parâmetros.
- Vetor enviado como texto no formato pgvector (`'[0.1,0.2,...]'`), convertido com `::vector`
  no SQL. **Não** usar a biblioteca `pgvector`.
- `response_json`: gravar a resposta como string JSON (`json.dumps(answer)` + `::jsonb` ou
  `psycopg.types.json.Jsonb`); na leitura, devolver somente o texto em `SemanticCacheMatch.response`.
- Falhas (`psycopg.Error`, incluindo conexão e dimensão incompatível):
  - em `find_nearest`: `logger.exception(...)` e retorno `[]` (miss);
  - em `save`: `logger.exception(...)` e retorno normal.
- Logs somente com hit/miss/gravação/falha e, no máximo, os 8 primeiros caracteres de uma chave;
  **nunca** pergunta, resposta, embedding ou senha.
</requirements>

## Subtarefas

- [x] 2.1 Criar `SemanticCacheEntry` e `SemanticCacheMatch` em `app/domain/cache.py` e exportá-los.
- [x] 2.2 Criar `app/infrastructure/postgres/client.py` (abertura da conexão assíncrona).
- [x] 2.3 Implementar `find_nearest` (SQL parametrizado, serialização do vetor, mapeamento das linhas).
- [x] 2.4 Implementar `save` (serialização do vetor e do `response_json`).
- [x] 2.5 Tratamento de falhas e logs conforme os requisitos.
- [x] 2.6 Testes de unidade.
- [x] 2.7 Testes de integração com o PostgreSQL mockado.

## Detalhes de Implementação

- Siga a estrutura de `app/infrastructure/redis/` (`client.py` + repositório + `__init__.py`) e o
  tratamento de falhas de `app/infrastructure/redis/answer_cache_repository.py`.
- SQL de consulta, colunas da tabela e regras de serialização: `../../.mine/cache_semantico.md`,
  seções 1.4, 2 e "Dados do PostgreSQL".
- Isolar helpers pequenos e puros (ex.: `_to_vector_literal(embedding) -> str`) para manter os
  métodos abaixo de 30 linhas e facilitar os testes.

## Critérios de Sucesso

- `find_nearest` devolve até `top_k` `SemanticCacheMatch` ordenados, filtrados pelo fingerprint.
- `save` grava todas as colunas exigidas, com `response_json` como string JSON.
- Qualquer erro do PostgreSQL vira `[]` (leitura) ou apenas log (escrita), sem exceção para o chamador.
- Nenhum valor concatenado no SQL; nenhum dado sensível nos logs.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/postgres/test_semantic_cache_repository.py`):
  - Vetor serializado no formato `'[0.1,0.2,...]'`.
  - `find_nearest` envia os parâmetros corretos (fingerprint, `limit` = `top_k`, vetor em texto).
  - Linhas retornadas viram `SemanticCacheMatch` com a resposta em texto, na ordem recebida.
  - Nenhuma linha → `[]`.
  - `psycopg.Error` na conexão ou na execução → `[]` e log de erro, sem exceção.
  - `save` envia todas as colunas, com `response_json` como string JSON.
  - `psycopg.Error` no `save` → apenas log, sem exceção.
  - Logs não contêm a pergunta nem a resposta (`caplog`).
- [x] Testes de integração (`tests/integration/postgres/test_semantic_cache_integration.py`):
  - Ciclo `save` → `find_nearest` com a conexão do `psycopg` mockada (cursor fake), validando o
    SQL composto com o nome da tabela da configuração e o mapeamento ida e volta.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/cache.py`
- `app/domain/__init__.py`
- `app/infrastructure/postgres/__init__.py` (novo)
- `app/infrastructure/postgres/client.py` (novo)
- `app/infrastructure/postgres/semantic_cache_repository.py` (novo)
- `app/infrastructure/redis/answer_cache_repository.py` (referência de padrão)
- `app/infrastructure/config/models.py` (apenas leitura)
- `tests/unit/postgres/test_semantic_cache_repository.py` (novo)
- `tests/integration/postgres/test_semantic_cache_integration.py` (novo)
