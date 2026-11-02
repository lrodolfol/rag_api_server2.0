# Tarefa 3.0: Serviço de aplicação de exclusão (`DeletionService`)

<critical>Ler os arquivos `delete-service.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar a camada de aplicação que orquestra a exclusão de um cliente, aplicando a regra de negócio:
**só exclui se houver vetores no Pinecone**; caso contrário, não faz nada.
Depende das Tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (regra de negócio na camada de aplicação, sem FastAPI)
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md` (não engolir exceções)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo modelo de domínio `CompanyDeletionRequest` com `user_code: str = Field(min_length=1)`
  em `app/domain/company.py`, exportado em `app/domain/__init__.py` (e em `app/api/schemas.py`, seguindo o padrão).
- Novo pacote `app/application/deletion/` com `DeletionService` (mesmo estilo de `RegistrationService`).
- O serviço recebe por construtor `PineconeVectorRepository` e `ClientStorageRepository`.
- Método `async def delete(self, request: CompanyDeletionRequest) -> None`:
  1. `has_vectors_for_user_code` → se `False`, logar "nenhum registro encontrado" e retornar;
  2. se `True`: `delete_by_user_code` no Pinecone e depois `delete_client` no S3.
- Erros dos repositórios (`VectorRepositoryError`, `ClientStorageError`) **propagam** (os handlers globais transformam em 5xx).
- Logs de observabilidade sem exagero: início, "sem registros" e conclusão. Nunca logar `user_code`.
</requirements>

## Subtarefas

- [x] 3.1 Criar `CompanyDeletionRequest` e exportá-lo.
- [x] 3.2 Criar `app/application/deletion/__init__.py` e `service.py` com `DeletionService`.
- [x] 3.3 Testes de unidade do modelo em `tests/unit/domain/test_company.py` (`user_code` vazio é inválido).
- [x] 3.4 Testes de unidade do serviço em `tests/unit/deletion/test_deletion_service.py` (repositórios mockados com `AsyncMock`):
  - com registros: chama delete no Pinecone **e** no S3, nessa ordem;
  - sem registros: não chama nenhum delete;
  - erro no Pinecone: propaga e **não** chama o S3;
  - erro no S3: propaga.
- [x] 3.5 Teste de integração do serviço com repositórios reais sobre clients fake (mesmo estilo de `tests/integration/pinecone` e `tests/integration/storage`).

## Detalhes de Implementação

- Regras de negócio: `delete-service.md` e a seção "Regras de negócio decididas" em `tasks/delete-service/tasks.md`.
- Usar `app/application/registration/service.py` como referência de estrutura, logging e injeção.

## Critérios de Sucesso

- A regra "sem vetores → nada acontece" é garantida por teste.
- O serviço não importa nada de FastAPI.
- Métodos com menos de 30 linhas; testes, linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (não aplicável nesta tarefa — ver Tarefa 4.0)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/company.py`, `app/domain/__init__.py`, `app/api/schemas.py`
- `app/application/deletion/` (novo)
- `tests/unit/domain/test_company.py`
- `tests/unit/deletion/test_deletion_service.py` (novo)
