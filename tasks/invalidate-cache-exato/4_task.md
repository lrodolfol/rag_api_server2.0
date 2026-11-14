# Tarefa 4.0: Invalidação do cache exato no cadastro/atualização e na exclusão, injeção de dependências e testes E2E

<critical>Ler os arquivos `../../meus_prompts/invalidate-cache-exato.md` (raiz), `tasks/invalidate-cache-exato/tasks.md`, `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O `RegistrationService` e o `DeletionService` já invalidam o cache semântico logo após
escrever no Pinecone. Esta tarefa faz os dois invalidarem **também** o cache exato, nos mesmos
pontos e com as mesmas categorias, usando `RedisAnswerCacheRepository.invalidate_category`
(tarefa 1.0). Inclui a injeção de dependências e os testes E2E da feature. Depende da tarefa
1.0 (as tarefas 2.0 e 3.0 são necessárias para que existam chaves indexadas no fluxo real).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviços de aplicação orquestram; nenhum comando Redis aqui)
- `.claude/code_patterns/python-conventions.md` (`register`/`delete` continuam < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha do cache não derruba a requisição; já tratada no repositório)
- `.claude/code_patterns/security.md` (logar só slugs; nunca `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `RegistrationService.__init__` e `DeletionService.__init__` ganham
  `answer_cache: RedisAnswerCacheRepository` (importado de `app.infrastructure.redis`).
- **Cadastro/atualização:** o helper `_invalidate_semantic_cache` passa a invalidar os dois
  caches (renomear para algo como `_invalidate_caches`). Para a categoria nova e, quando
  `previous_slug` existe e é diferente, para a anterior: chamar
  `self._semantic_cache.invalidate_category(slug)` e `self._answer_cache.invalidate_category(slug)`.
  Sem chamadas duplicadas quando a categoria não mudou.
- **Exclusão:** logo após `invalidate_category` do cache semântico, chamar
  `self._answer_cache.invalidate_category(category_slug)` (`None` para cliente legado). Cliente
  sem vetores: nada é invalidado.
- Conteúdo rejeitado pela moderação continua sem nenhuma escrita nem invalidação.
- Ordem preservada: Pinecone → invalidação (semântico e exato) → bucket.
- `app/api/dependencies.py`: `get_registration_service` e `get_deletion_service` passam
  `answer_cache=_answer_cache_repository()` (provider já existente).
- Atualizar as docstrings dos módulos de cadastro e exclusão (passos do fluxo).
- Contratos HTTP não mudam: 201 no cadastro e resposta atual na exclusão mesmo com falha do Redis.
</requirements>

## Subtarefas

- [x] 4.1 Injetar `answer_cache` no `RegistrationService` e invalidar categoria nova/anterior.
- [x] 4.2 Injetar `answer_cache` no `DeletionService` e invalidar a categoria dos vetores.
- [x] 4.3 Atualizar `get_registration_service` e `get_deletion_service` em `app/api/dependencies.py`.
- [x] 4.4 Atualizar docstrings.
- [x] 4.5 Atualizar fixtures/testes existentes que constroem esses serviços
  (`tests/unit/registration/`, `tests/unit/deletion/`, `tests/integration/api/`,
  `tests/integration/deletion/`, `tests/integration/conftest.py`).
- [x] 4.6 Testes de unidade, de integração e E2E.

## Detalhes de Implementação

- Pontos e regras de invalidação (categoria nova + anterior; legado `None`; cliente sem vetores):
  `tasks/invalidate-cache/tasks.md`, "Quando invalidar", e `tasks/invalidate-cache/4_task.md` / `5_task.md`.
- Implementação atual: `app/application/registration/service.py` (`_invalidate_semantic_cache`)
  e `app/application/deletion/service.py` (`delete`).

## Critérios de Sucesso

- Primeiro cadastro / recadastro na mesma categoria `alimentacao`: `answer_cache.invalidate_category`
  chamado uma vez com `"alimentacao"`.
- Recadastro mudando de `beleza` para `alimentacao`: chamado com as duas categorias.
- Exclusão de cliente em `alimentacao`: chamado com `"alimentacao"`; cliente legado: com `None`;
  cliente sem vetores: não chamado.
- Moderação rejeitada: não chamado.
- A invalidação do cache exato acontece depois de `upsert_company_vectors` / `delete_by_user_code`
  e antes das escritas no bucket (ordem verificada com `MagicMock.attach_mock`).
- Redis indisponível na invalidação → cadastro e exclusão respondem com sucesso.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/registration/test_registration_service.py`,
  `tests/unit/deletion/test_deletion_service.py`, `AsyncMock` para `answer_cache`): todos os
  cenários dos critérios, incluindo a ordem e a ausência de `user_code` nos logs.
- [x] Testes de integração (`tests/integration/api/test_registration_api.py`,
  `tests/integration/api/test_deletion_api.py`, `tests/integration/deletion/test_deletion_integration.py`,
  com `RedisAnswerCacheRepository` real sobre `FakeAsyncRedis`): respostas pré-gravadas em
  `alimentacao`, `beleza` e `None` → após cadastro/exclusão em `alimentacao`, só as de `beleza`
  continuam no Redis; falha simulada do Redis → status de sucesso mantido.
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`): busca classificada em
  `alimentacao` grava a resposta → `POST /companies` em `alimentacao` → a mesma pergunta não
  acerta mais o cache exato (pipeline/semântico é consultado); uma resposta em `beleza`
  continua acertando o cache exato. Cenário equivalente para `DELETE /companies` e para a
  mudança de categoria (as duas categorias invalidadas).

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/registration/service.py`
- `app/application/deletion/service.py`
- `app/api/dependencies.py`
- `tests/unit/registration/test_registration_service.py`
- `tests/unit/deletion/test_deletion_service.py`
- `tests/integration/api/test_registration_api.py`
- `tests/integration/api/test_deletion_api.py`
- `tests/integration/deletion/test_deletion_integration.py`
- `tests/integration/api/test_e2e_flows.py`
- `tests/integration/conftest.py`
