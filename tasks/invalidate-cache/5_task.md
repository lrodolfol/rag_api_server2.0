# Tarefa 5.0: Invalidação na exclusão (`DeletionService`), injeção de dependências e testes E2E

<critical>Ler os arquivos `../../meus_prompts/invalid-cache-on-new-service.md` (raiz), `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Quando um serviço é excluído (`DELETE /companies`), as respostas do cache semântico da
categoria dele ainda o indicariam. Esta tarefa faz o `DeletionService`
(`app/application/deletion/service.py`) invalidar a categoria lida dos vetores do cliente,
usando o `SemanticCacheService`, inclui a injeção da dependência e fecha a feature com os testes
E2E do ciclo completo (busca → cache → cadastro/exclusão → busca de novo sem cache).
Depende das tarefas 1.0, 2.0, 3.0 e 4.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviço de aplicação orquestra; sem SQL nem `psycopg` aqui)
- `.claude/code_patterns/python-conventions.md` (`delete` continua < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha do cache não derruba a exclusão; erros de Pinecone/bucket continuam propagando)
- `.claude/code_patterns/security.md` (nunca logar `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `DeletionService.__init__` ganha o parâmetro `semantic_cache: SemanticCacheService`.
- Em `delete`, **imediatamente após** `delete_by_user_code` no Pinecone e **antes** de
  `_delete_stored_record`, chamar `self._semantic_cache.invalidate_category(category_slug)`.
  - `category_slug` é o valor já lido por `get_category_by_user_code` (antes da exclusão).
  - Cliente legado (`category_slug is None`): a chamada é feita com `None`, o que apaga só as
    linhas sem categoria (regra do SQL da tarefa 1.0). O `warning` existente sobre o bucket
    continua.
- Cliente **sem vetores**: nada é feito, inclusive nenhuma invalidação (mantém "não faz nada").
- Falha do PostgreSQL na invalidação é logada pelo repositório e a exclusão continua (200).
  Erros de `VectorRepositoryError`/`ClientStorageError` continuam propagando como hoje.
- `app/api/dependencies.py`: `get_deletion_service` passa `semantic_cache=_semantic_cache_service()`.
- Atualizar a docstring do módulo com o passo de invalidação.
</requirements>

## Subtarefas

- [ ] 5.1 Receber `semantic_cache` no construtor e chamar `invalidate_category(category_slug)`
  logo após a exclusão dos vetores.
- [ ] 5.2 Atualizar `get_deletion_service` em `app/api/dependencies.py`.
- [ ] 5.3 Atualizar docstring do módulo.
- [ ] 5.4 Atualizar as fixtures/testes existentes que constroem `DeletionService`
  (`tests/unit/deletion/test_deletion_service.py`,
  `tests/integration/deletion/test_deletion_integration.py`,
  `tests/integration/api/test_deletion_api.py`, `tests/integration/api/test_e2e_flows.py`).
- [ ] 5.5 Testes de unidade e de integração da invalidação na exclusão.
- [ ] 5.6 Testes E2E do ciclo completo da feature.
- [ ] 5.7 Rodar a suíte inteira, lint e type checker dentro do `.venv`; marcar as tarefas em
  `tasks/invalidate-cache/tasks.md`.

## Detalhes de Implementação

- Fluxo atual de `delete` (verificação, leitura da categoria, exclusão de vetores, bucket):
  `app/application/deletion/service.py`.
- Método `invalidate_category` e o que ele apaga: tarefas 1.0 e 2.0 e
  `tasks/invalidate-cache/tasks.md`.
- Montagem dos serviços reais com dependências fake nos E2E (`_search_service`,
  `_FakeVectorRepository`, `semantic_cache_db`): `tests/integration/api/test_e2e_flows.py`.

## Critérios de Sucesso

- Cliente com vetores em `beleza`: ordem `get_category_by_user_code` → `delete_by_user_code` →
  `invalidate_category("beleza")` → `delete_client` (verificada com `attach_mock`).
- Cliente legado sem categoria: `invalidate_category(None)` chamado; bucket não tocado.
- Cliente sem vetores: `invalidate_category` nunca chamado.
- `DELETE /companies` responde 200 mesmo com falha do PostgreSQL na invalidação.
- E2E: uma pergunta respondida pelo RAG e gravada no cache semântico em `alimentacao`; após
  cadastrar outro serviço em `alimentacao` (ou excluir o existente), a mesma pergunta com texto
  **diferente** (para não bater no cache exato) volta a rodar o pipeline (contagem de chamadas
  ao fake da OpenAI/Pinecone aumenta) e as linhas de `alimentacao` sumiram de
  `semantic_cache_db.rows`; entradas de outra categoria permanecem.
- Suíte completa, lint e type checker sem falhas.

## Testes da Tarefa

- [ ] Testes de unidade (`tests/unit/deletion/test_deletion_service.py`, `AsyncMock` para
  `semantic_cache`): os três cenários de serviço acima (categoria conhecida com ordem, legado
  `None`, sem vetores) e verificação de que `user_code` não aparece nos logs.
- [ ] Testes de integração:
  - `tests/integration/deletion/test_deletion_integration.py`: `SemanticCacheService` real sobre
    `semantic_cache_db`; linhas em `beleza`, `alimentacao` e `None` → após excluir cliente de
    `beleza`, restam só as de `alimentacao`.
  - `tests/integration/api/test_deletion_api.py`: 200 com falha simulada do PostgreSQL.
- [ ] Testes E2E (`tests/integration/api/test_e2e_flows.py`):
  - busca → cache semântico gravado com categoria → `POST /companies` na mesma categoria →
    nova busca semanticamente igual não usa o cache semântico;
  - busca → cache gravado → `DELETE /companies` do cliente da categoria → nova busca não usa o
    cache semântico;
  - entradas de outra categoria continuam servindo hit semântico após cadastro/exclusão.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/deletion/service.py`
- `app/api/dependencies.py`
- `tests/unit/deletion/test_deletion_service.py`
- `tests/integration/deletion/test_deletion_integration.py`
- `tests/integration/api/test_deletion_api.py`
- `tests/integration/api/test_e2e_flows.py`
- `tasks/invalidate-cache/tasks.md`
