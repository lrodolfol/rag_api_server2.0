# Tarefa 1.0: `RedisAnswerCacheRepository`: índice SET por categoria e `invalidate_category`

<critical>Ler os arquivos `../../meus_prompts/invalidate-cache-exato.md` (raiz), `tasks/invalidate-cache-exato/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje o repositório do cache exato (`app/infrastructure/redis/answer_cache_repository.py`) só
grava e lê `rag_answer_cache:<hash>`. Esta tarefa faz o `set` também registrar o hash no SET
de cada categoria da resposta (`rag_answer_cache:category:<slug>`, ou `__none__` para resposta
sem categoria) e cria `invalidate_category`, que apaga as respostas indexadas em uma categoria.
É a base das tarefas 3.0 e 4.0 e não depende de nenhuma outra.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (só o repositório conhece comandos Redis)
- `.claude/code_patterns/python-conventions.md` (tipagem completa, métodos < 30 linhas, constantes `Final`)
- `.claude/code_patterns/error-handling.md` (`RedisError` logado e nunca propagado)
- `.claude/code_patterns/security.md` (logar só slug e prefixo de 8 caracteres do hash)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Nova constante para o prefixo do índice (ex.:
  `ANSWER_CACHE_CATEGORY_PREFIX: Final[str] = "rag_answer_cache:category"`) e para o
  marcador sem categoria (ex.: `UNCATEGORIZED_SLUG: Final[str] = "__none__"`). Exportar o que
  os testes precisarem em `app/infrastructure/redis/__init__.py`.
- `set(cache_key, answer, category_slugs: set[str | None])`: numa **única transação**
  (`self._client.pipeline(transaction=True)`) grava a resposta com `ex=ANSWER_CACHE_TTL_SECONDS`
  e faz `SADD <set da categoria> cache_key` para cada slug (`None` → `__none__`). Os SETs
  **não** recebem TTL. O parâmetro é obrigatório (todo chamador tem que decidir a categoria).
- `invalidate_category(category_slug: str | None) -> None`:
  - slug → processa o SET do slug e o SET `__none__`; `None` → só o SET `__none__`;
  - por SET: `SMEMBERS`; se vazio, nada; senão, numa transação, `DEL` das chaves
    `rag_answer_cache:<membro>` e `SREM` dos membros lidos (não `DEL` do SET);
  - slug em branco (`""`, `"  "`) é erro do chamador → `ValueError` (mesma regra de
    `SemanticCacheService.invalidate_category`);
  - `RedisError` → `logger.exception(...)` com a categoria, sem propagar;
  - log de sucesso com a categoria e a quantidade de chaves apagadas.
- `get` não muda (continua só lendo/renovando a chave da resposta).
- Atualizar a docstring do módulo explicando o índice, o SET `__none__` e por que o SET não tem TTL.
- Manter cada método com menos de 30 linhas (extrair helpers como `_category_key(slug)` e
  `_invalidate_set(set_key)`).
</requirements>

## Subtarefas

- [x] 1.1 Criar as constantes e o helper que monta a chave do SET (`None` → `__none__`).
- [x] 1.2 Alterar `set` para gravar resposta + `SADD` em transação.
- [x] 1.3 Criar `invalidate_category` (validação do slug, SET da categoria + `__none__`).
- [x] 1.4 Atualizar docstring e exports do pacote `app/infrastructure/redis`.
- [x] 1.5 Ajustar os testes existentes que chamam `set` sem categoria
  (`tests/unit/redis/test_answer_cache_repository.py`,
  `tests/integration/redis/test_answer_cache_integration.py`).
- [x] 1.6 Testes de unidade e de integração novos.

## Detalhes de Implementação

- Comportamento atual de `get`/`set`, TTL deslizante e padrão de logs:
  `app/infrastructure/redis/answer_cache_repository.py` e `tasks/cache/tasks.md`.
- Regras do índice, do SET `__none__` e da remoção por `SREM`: `tasks/invalidate-cache-exato/tasks.md`,
  "Regras de negócio decididas".
- O cliente Redis é criado com `decode_responses=True` (ver `app/api/dependencies.py` e a
  fixture `FakeAsyncRedis(decode_responses=True)`), então `SMEMBERS` devolve `set[str]`.

## Critérios de Sucesso

- `set("abc...", json, {"alimentacao"})` → existe `rag_answer_cache:abc...` com TTL de 24h e
  `abc...` é membro de `rag_answer_cache:category:alimentacao`, que não tem TTL (`TTL = -1`).
- `set(..., {None})` → membro de `rag_answer_cache:category:__none__`.
- `set(..., {"alimentacao", "beleza"})` → membro dos dois SETs.
- Com respostas em `alimentacao`, `beleza` e `__none__`, `invalidate_category("alimentacao")`
  apaga as respostas de `alimentacao` e `__none__`; as de `beleza` continuam acessíveis por `get`.
- `invalidate_category(None)` apaga só as de `__none__`.
- `invalidate_category("")` levanta `ValueError`.
- Falha do Redis (`RedisError`) em `set` ou `invalidate_category` é logada e não propaga.
- Logs não contêm a resposta nem o hash completo.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/redis/test_answer_cache_repository.py`, cliente mockado):
  transação usada no `set`; `SADD` por categoria; `None` → `__none__`; `ValueError` para slug em
  branco; `RedisError` logado e engolido em `set` e `invalidate_category`; SET vazio não faz
  `DEL`; logs sem resposta nem hash completo.
- [x] Testes de integração (`tests/integration/redis/test_answer_cache_integration.py`,
  `FakeAsyncRedis`): os cenários de "Critérios de Sucesso" ponta a ponta, incluindo
  `TTL = -1` do SET e a remoção dos membros após a invalidação.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/redis/answer_cache_repository.py`
- `app/infrastructure/redis/__init__.py`
- `tests/unit/redis/test_answer_cache_repository.py`
- `tests/integration/redis/test_answer_cache_integration.py`
