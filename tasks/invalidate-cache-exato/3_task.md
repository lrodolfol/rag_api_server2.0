# Tarefa 3.0: `SearchService` indexa as respostas do cache exato pela(s) categoria(s)

<critical>Ler os arquivos `../../meus_prompts/invalidate-cache-exato.md` (raiz), `tasks/invalidate-cache-exato/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O `SearchService` (`app/application/search/service.py`) grava no cache exato em dois pontos.
Esta tarefa faz cada um informar ao `RedisAnswerCacheRepository.set` (tarefa 1.0) as
categorias da resposta, para que ela possa ser invalidada depois. Depende das tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviço orquestra; nenhum comando Redis aqui)
- `.claude/code_patterns/python-conventions.md` (métodos < 30 linhas, tipagem)
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/security.md`
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- **Pipeline RAG** (`_store_answer`): `self._answer_cache.set(cache_key, answer.to_json(), {category_slug})`,
  usando o mesmo `category_slug` já repassado ao cache semântico (`None` quando a busca rodou
  sem filtro).
- **Hit semântico** (`_answer_from_semantic_cache`): a chave é indexada nas categorias dos
  matches **aceitos** pelo threshold (os que entraram na fusão), ex.:
  `{match.category for match in accepted}`. Matches abaixo do threshold ou com JSON inválido
  não contam.
- `threshold_evaluate` é público e usado em testes: preservar sua assinatura e retorno. Para
  obter os matches aceitos, extrair um helper (ex.: `_accepted_matches(matches)`) usado tanto
  por `threshold_evaluate` quanto pelo cálculo das categorias, sem duplicar a regra do
  threshold nem a validação do JSON.
- Hit no cache exato (`_get_cached_answer`) não muda (não reindexa).
- Atualizar a docstring do módulo (passos do fluxo) mencionando a indexação por categoria.
</requirements>

## Subtarefas

- [x] 3.1 Passar `{category_slug}` no `set` de `_store_answer`.
- [x] 3.2 Extrair o helper dos matches aceitos e calcular as categorias no hit semântico.
- [x] 3.3 Passar as categorias no `set` de `_answer_from_semantic_cache`.
- [x] 3.4 Atualizar docstring.
- [x] 3.5 Testes de unidade e de integração.

## Detalhes de Implementação

- Fluxo de busca, threshold e fusão de respostas: `app/application/search/service.py` e
  `tasks/semantic-cache-threshold/tasks.md`.
- Regra "categoria(s) de uma chave": `tasks/invalidate-cache-exato/tasks.md`.

## Critérios de Sucesso

- Pergunta classificada em `alimentacao` → `set` chamado com `{"alimentacao"}`.
- Busca sem filtro (classificação falhou/catálogo vazio) → `set` chamado com `{None}`.
- Hit semântico com matches aceitos de `alimentacao` e `None` e um match de `beleza` abaixo do
  threshold → `set` chamado com `{"alimentacao", None}`.
- Resposta não cacheável → `set` não é chamado (comportamento atual mantido).
- Hit no cache exato → `set` não é chamado.
- Testes existentes de `threshold_evaluate` continuam passando sem alteração.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/search/test_search_service.py`, `AsyncMock` para
  `answer_cache`): os cenários dos critérios acima, verificando o terceiro argumento de `set`.
- [x] Testes de integração (`tests/integration/api/` — fluxo de busca com `FakeAsyncRedis`):
  após uma busca classificada em `alimentacao`, o hash da pergunta está em
  `rag_answer_cache:category:alimentacao`; após um hit semântico, está nos SETs das categorias
  dos matches aceitos.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_e2e_flows.py`
- `tests/integration/conftest.py`
