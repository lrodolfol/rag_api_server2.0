# Tarefa 3.0: `SearchService` grava a categoria da pergunta no cache semântico

<critical>Ler os arquivos `../../meus_prompts/invalid-cache-on-new-service.md` (raiz), `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Sem a categoria gravada, a invalidação por categoria não tem o que filtrar. Hoje
`SearchService._run_pipeline` (`app/application/search/service.py`) classifica a pergunta em
`_classify_question`, usa o slug só no filtro do Pinecone e o descarta. Esta tarefa faz o slug
chegar até `_store_answer`, que o repassa para `SemanticCacheService.store`. O comportamento
visível ao usuário (mensagens, histórico, cache exato, hit/miss) **não muda**.
Depende da tarefa 2.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (orquestração só no serviço de aplicação)
- `.claude/code_patterns/python-conventions.md` (preferir modelo/`NamedTuple` tipado a tupla anônima; métodos < 30 linhas)
- `.claude/code_patterns/security.md` (logar só a categoria; nunca pergunta, resposta ou `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `_run_pipeline` passa a devolver a resposta **e** o slug da categoria usado na busca
  (`str | None`). Sugestão: um `NamedTuple`/modelo imutável pequeno e privado do módulo (ex.:
  `_PipelineResult(answer, category_slug)`) em vez de tupla anônima, para manter a leitura clara.
- `_answer_on_cache_miss` repassa o slug para `_store_answer`, que chama
  `self._semantic_cache.store(fingerprint, question, answer, embedding, category_slug=...)`.
- Busca sem filtro (catálogo vazio, classificação falhou com `OpenIaException` ou categoria
  desconhecida) grava a entrada com `category_slug=None`.
- O cache exato (Redis) **não muda**: chave, conteúdo e momento de gravação iguais aos de hoje.
- Nenhuma chamada extra à LLM: a classificação continua acontecendo uma única vez, somente em
  miss dos dois caches, como hoje.
- Atualizar a docstring do módulo (item "store the answer JSON in the exact and semantic
  caches") para citar que a categoria da pergunta é gravada no cache semântico.
- `_run_pipeline`, `_answer_on_cache_miss` e `_store_answer` continuam com menos de 30 linhas.
</requirements>

## Subtarefas

- [ ] 3.1 Fazer `_run_pipeline` devolver resposta + slug da categoria (tipo nomeado).
- [ ] 3.2 Propagar o slug em `_answer_on_cache_miss` → `_store_answer` → `store`.
- [ ] 3.3 Atualizar docstring do módulo.
- [ ] 3.4 Atualizar os testes de unidade existentes que fazem `store.assert_awaited_once_with(...)`
  e criar os novos.
- [ ] 3.5 Testes de integração/E2E verificando a coluna `category` no banco em memória.

## Detalhes de Implementação

- Fluxo atual de miss (embedding único, cache semântico, pipeline, `_store_answer`):
  `app/application/search/service.py`, métodos `_answer_on_cache_miss`, `_run_pipeline`,
  `_store_answer` e `_classify_question`.
- Assinatura nova de `store`: tarefa 2.0.
- Regra "busca sem filtro → `category = NULL`": `tasks/invalidate-cache/tasks.md`.

## Critérios de Sucesso

- Em miss semântico com pergunta classificada em `alimentacao`, `store` é chamado com
  `category_slug="alimentacao"`.
- Em miss semântico com busca sem filtro (qualquer um dos três motivos), `store` é chamado com
  `category_slug=None`.
- Em hit exato e em hit semântico, `store` continua **não** sendo chamado.
- Resposta não cacheável continua sem gravar em nenhum cache.
- Todos os testes de `tests/unit/search/` e `tests/integration/api/` continuam passando.

## Testes da Tarefa

- [ ] Testes de unidade (`tests/unit/search/test_search_service.py`, mocks existentes):
  - miss semântico + categoria conhecida → `store` recebe o slug;
  - miss semântico + catálogo vazio → `store` recebe `None`;
  - miss semântico + `OpenIaException` na classificação → `store` recebe `None`;
  - miss semântico + categoria desconhecida pela LLM → `store` recebe `None`;
  - ajustar `test_should_run_rag_and_store_json_in_both_caches_on_semantic_miss` e
    `test_should_run_rag_when_all_semantic_matches_are_below_threshold` para o novo argumento.
- [ ] Testes de integração (`tests/integration/api/test_e2e_flows.py`, serviço real com
  `semantic_cache_db`): após uma busca classificada em uma categoria, a linha gravada em
  `semantic_cache_db.rows` tem `category` igual ao slug; após uma busca sem categoria no
  catálogo, `category` é `None`.
- [ ] Testes E2E: cobertos pelo item acima.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_e2e_flows.py`
- `tests/integration/conftest.py` (banco em memória do cache semântico, já atualizado na 1.0)
