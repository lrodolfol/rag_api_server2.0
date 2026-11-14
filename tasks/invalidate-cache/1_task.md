# Tarefa 1.0: Categoria na entrada do cache semântico e `delete_by_category` no repositório PostgreSQL

<critical>Ler os arquivos `../../meus_prompts/invalid-cache-on-new-service.md` (raiz), `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje o `INSERT` do cache semântico não grava a coluna `category` e não existe nenhuma forma de
apagar entradas por categoria. Esta tarefa adiciona o campo `category` ao modelo de domínio
`SemanticCacheEntry`, passa a gravá-lo no `INSERT` e cria o método `delete_by_category` no
`PostgresSemanticCacheRepository`. Nenhum fluxo de negócio é alterado ainda: o `SearchService`
e o `SemanticCacheService` continuam funcionando (a categoria fica `None` até a tarefa 3.0).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (só o repositório conhece SQL e `psycopg`; domínio sem infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, modelos Pydantic imutáveis, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha do banco é logada e nunca propagada pelo cache)
- `.claude/code_patterns/security.md` (SQL parametrizado; nunca logar pergunta, resposta ou embedding)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `SemanticCacheEntry` (`app/domain/cache.py`) ganha o campo `category: str | None = None`
  (slug da categoria; `None` quando a busca rodou sem filtro). O modelo continua `frozen`.
- `INSERT_SQL` (`app/infrastructure/postgres/semantic_cache_repository.py`) passa a incluir a
  coluna `category` e `_to_insert_params` passa a enviar `"category": entry.category`
  (`None` vira `NULL`).
- Nova constante `DELETE_BY_CATEGORY_SQL`, no mesmo padrão das demais (`sql.SQL` com
  `{table}` via `sql.Identifier`), exatamente:
  `DELETE FROM {table} WHERE category IS NULL OR category = %(category)s`.
  A query é composta uma única vez no `__init__`, como `_find_nearest_query` e `_insert_query`.
- Novo método `async def delete_by_category(self, category_slug: str | None) -> None`:
  - executa o `DELETE` com `{"category": category_slug}`;
  - em `psycopg.Error`: `logger.exception("Failed to invalidate semantic cache (category='%s')", ...)`
    e retorna (nunca levanta);
  - em sucesso: `logger.info` com a categoria (`"none"` quando `None`) e a quantidade de linhas
    apagadas (`cursor.rowcount`). Para obter o `rowcount`, `_execute` pode passar a devolver o
    cursor retornado por `connection.execute(...)` (ou criar um helper equivalente); `save`
    continua ignorando o retorno.
- `find_nearest` **não muda** (a leitura continua sem filtro de categoria: o filtro é
  responsabilidade da classificação da pergunta na busca).
- Nenhum valor fixo no SQL; nome da tabela continua vindo de `SemanticCacheConfig.table`.
- Atualizar a docstring do módulo do repositório para citar a invalidação por categoria.
</requirements>

## Subtarefas

- [x] 1.1 Adicionar `category: str | None = None` em `SemanticCacheEntry` e atualizar a docstring
  do módulo `app/domain/cache.py`.
- [x] 1.2 Incluir `category` no `INSERT_SQL` e em `_to_insert_params`.
- [x] 1.3 Criar `DELETE_BY_CATEGORY_SQL`, compor no `__init__` e implementar `delete_by_category`
  (com log de categoria e `rowcount`, falha só logada).
- [x] 1.4 Atualizar o banco em memória dos testes de integração
  (`InMemorySemanticCacheDatabase.execute` em `tests/integration/conftest.py`) para tratar
  `DELETE`: remover as linhas com `category is None` ou `category == params["category"]` e
  expor um contador de linhas apagadas (ou `rowcount` no cursor fake). O `INSERT` em memória já
  guarda `params`, então a chave `category` passa a existir nas linhas automaticamente.
- [x] 1.5 Testes de unidade (modelo, `INSERT` e `delete_by_category`).
- [x] 1.6 Testes de integração (round trip `save` → `delete_by_category` → `find_nearest`).

## Detalhes de Implementação

- Padrões de SQL composto, parâmetros nomeados, tratamento de `psycopg.Error` e logs:
  `app/infrastructure/postgres/semantic_cache_repository.py` (métodos `find_nearest` e `save`).
- Regra do `DELETE` (apagar a categoria **e** as linhas `NULL`; `None` apaga só `NULL`):
  `tasks/invalidate-cache/tasks.md`, seção "Regras de negócio decididas".
- Conexão por operação com commit/rollback automático: `app/infrastructure/postgres/client.py`.

## Critérios de Sucesso

- `SemanticCacheEntry(...)` sem `category` continua válido (default `None`); com
  `category="alimentacao"` guarda o slug.
- O `INSERT` envia a coluna `category` com o slug ou `NULL`.
- `delete_by_category("alimentacao")` executa um único `DELETE` parametrizado com
  `{"category": "alimentacao"}`; `delete_by_category(None)` envia `{"category": None}`.
- Falha de conexão ou do `DELETE` é logada com `logger.exception` e não levanta exceção.
- Nenhum log contém pergunta, resposta ou embedding.
- Todos os testes que já existiam continuam passando (`python -m pytest` dentro do `.venv`).

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/domain/test_cache.py` (criar, se não existir): `category` default `None`,
    aceita slug, modelo continua imutável.
  - `tests/unit/postgres/test_semantic_cache_repository.py` (usar `FakeConnection` existente):
    - `save` envia `category` nos parâmetros (slug e `None`) e o SQL renderizado contém a
      coluna `category`;
    - `delete_by_category` envia o SQL de `DELETE` com `{"category": slug}` e com
      `{"category": None}`;
    - `delete_by_category` só loga (`caplog`, nível `ERROR`) quando a conexão ou o `DELETE`
      falham com `psycopg.Error`;
    - o log de sucesso contém a categoria e não contém pergunta, resposta ou embedding.
- [x] Testes de integração (`tests/integration/postgres/test_semantic_cache_integration.py`,
  fixture `semantic_cache_db`):
  - `save` de entradas em `alimentacao`, `beleza` e `None`; `delete_by_category("alimentacao")`
    remove as de `alimentacao` e as `None`, mantém as de `beleza`; `find_nearest` depois
    devolve só `beleza`;
  - `delete_by_category(None)` remove apenas as entradas sem categoria;
  - `delete_by_category` em tabela vazia não falha;
  - falha simulada (`semantic_cache_db.error`) não levanta exceção.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/cache.py`
- `app/infrastructure/postgres/semantic_cache_repository.py`
- `tests/integration/conftest.py` (banco em memória do cache semântico)
- `tests/unit/domain/test_cache.py` (novo)
- `tests/unit/postgres/test_semantic_cache_repository.py`
- `tests/integration/postgres/test_semantic_cache_integration.py`
