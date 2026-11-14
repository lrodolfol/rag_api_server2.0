# Tarefa 2.0: `SemanticCacheMatch` passa a trazer a categoria da entrada do cache semântico

<critical>Ler os arquivos `../../meus_prompts/invalidate-cache-exato.md` (raiz), `tasks/invalidate-cache-exato/tasks.md`, `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Quando a busca acerta o cache semântico, a resposta (fusão dos matches) também é gravada no
cache exato. Para indexar essa chave nos SETs certos (tarefa 3.0), cada match precisa dizer a
categoria da linha do PostgreSQL de onde veio. A coluna `category` já é gravada desde a feature
`invalidate-cache`; esta tarefa só passa a **lê-la** em `find_nearest` e expô-la em
`SemanticCacheMatch`. Independente da tarefa 1.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (SQL só no repositório; domínio sem infraestrutura)
- `.claude/code_patterns/python-conventions.md` (modelo Pydantic imutável e tipado)
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `SemanticCacheMatch` (`app/domain/cache.py`) ganha `category: str | None = Field(default=None, min_length=1)`,
  mesmo formato do campo de `SemanticCacheEntry`. `None` = entrada sem categoria.
- `FIND_NEAREST_SQL` (`app/infrastructure/postgres/semantic_cache_repository.py`) seleciona
  também `c.category`; `_to_match` preenche o campo.
- Nada mais muda: filtro por fingerprint, `ORDER BY`, `LIMIT`, tratamento de erro e logs
  continuam iguais. `SemanticCacheService.find_answer` apenas repassa os matches.
- Atualizar as docstrings do domínio e do repositório mencionando que o match traz a categoria.
</requirements>

## Subtarefas

- [x] 2.1 Adicionar `category` a `SemanticCacheMatch`.
- [x] 2.2 Incluir `c.category` no `SELECT` e no `_to_match`.
- [x] 2.3 Atualizar docstrings.
- [x] 2.4 Testes de unidade e de integração.

## Detalhes de Implementação

- Coluna `category` e regra do `NULL`: `tasks/invalidate-cache/tasks.md`, "Regras de negócio decididas".
- Repositório atual: `app/infrastructure/postgres/semantic_cache_repository.py` (`find_nearest`, `_to_match`).

## Critérios de Sucesso

- Linha gravada com `category = 'alimentacao'` volta em `find_nearest` com
  `match.category == "alimentacao"`; linha com `NULL` volta com `match.category is None`.
- `SemanticCacheMatch(..., category="")` é rejeitado pela validação.
- Todos os testes existentes do cache semântico e do `SearchService` continuam passando sem
  alteração de comportamento.

## Testes da Tarefa

- [x] Testes de unidade: `tests/unit/domain/test_cache.py` (campo opcional, default `None`,
  `""` inválido); `tests/unit/postgres/test_semantic_cache_repository.py` (`_to_match` com e sem
  categoria; SQL contém `category`).
- [x] Testes de integração: `tests/integration/postgres/test_semantic_cache_integration.py`
  (gravar entradas com `alimentacao` e `None` e conferir `match.category` no `find_nearest`).

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/cache.py`
- `app/infrastructure/postgres/semantic_cache_repository.py`
- `tests/unit/domain/test_cache.py`
- `tests/unit/postgres/test_semantic_cache_repository.py`
- `tests/integration/postgres/test_semantic_cache_integration.py`
