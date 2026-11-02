# Tarefa 4.0: Endpoint `DELETE /companies`

<critical>Ler os arquivos `delete-service.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Expor o fluxo de exclusão via HTTP: `DELETE /companies` com body `{"user_code": "..."}`,
delegando ao `DeletionService` (Tarefa 3.0) e respondendo no envelope padrão `ApiResponse`.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/api.md` (rotas em `app/api/routes`, envelope de resposta, handler fino)
- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/error-handling.md` (não expor detalhes internos)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Rota `DELETE /companies` no **mesmo router** de `app/api/routes/registration.py` (mesmo recurso `/companies`), recebendo `CompanyDeletionRequest` no body.
- Handler fino: apenas delega a `DeletionService.delete` e retorna
  `ApiResponse(status_code=200, message="Company deleted successfully")` — a mesma resposta 200 com ou sem registros.
- Novo provider `get_deletion_service()` em `app/api/dependencies.py`, reutilizando os repositórios já cacheados (`_vector_repository`, `_storage_repository`).
- Body inválido (sem `user_code` / vazio) → 4xx, mantendo o mesmo comportamento atual do `POST /companies` (422).
- Erros internos → 5xx genérico pelos handlers já registrados em `app/api/errors/handlers.py` (não criar handlers novos).
- Não alterar o contrato do `POST /companies`.
</requirements>

## Subtarefas

- [x] 4.1 Adicionar `get_deletion_service` em `app/api/dependencies.py`.
- [x] 4.2 Adicionar o handler `DELETE /companies` em `app/api/routes/registration.py`.
- [x] 4.3 Testes de integração em `tests/integration/api/test_deletion_api.py` (TestClient + `dependency_overrides` com service fake):
  - 200 quando há registros;
  - 200 quando não há registros;
  - 422 com body vazio e com `user_code` vazio;
  - 500 com envelope genérico quando o service levanta `VectorRepositoryError`/`ClientStorageError` (sem vazar detalhes).
- [x] 4.4 Teste E2E em `tests/integration/api/test_e2e_flows.py`: cadastro (`POST /companies`) → exclusão (`DELETE /companies`) → verificar que vetores e registro S3 foram removidos (repositórios sobre clients fake).
- [x] 4.5 Atualizar o `README.md` com o novo endpoint (se o README documentar os endpoints). — N/A: o README não documenta endpoints.

## Detalhes de Implementação

- Requisitos do endpoint: `delete-service.md`.
- Referência de estrutura: rota `register_company` e testes em `tests/integration/api/test_registration_api.py`.

## Critérios de Sucesso

- `DELETE /companies` responde 200 / 4xx / 5xx conforme o requisito, sempre no envelope `ApiResponse`.
- Handler sem lógica de negócio.
- Suíte completa (`python -m pytest`) passa dentro do `.venv`, assim como linter e type checker.

## Testes da Tarefa

- [x] Testes de unidade (cobertos nas Tarefas 1.0–3.0)
- [x] Testes de integração
- [x] Testes E2E — cadastro → exclusão → verificação (mock)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/api/routes/registration.py`
- `app/api/dependencies.py`
- `tests/integration/api/test_deletion_api.py` (novo)
- `tests/integration/api/test_e2e_flows.py`
- `README.md`
