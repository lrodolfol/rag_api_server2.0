# Tarefa 4.0: Armazenamento do cliente por categoria no bucket S3

<critical>Ler os arquivos `../../meus_prompts/divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje todos os clientes ficam num único objeto, `client_services.jsonl`. Esta tarefa faz o
`ClientStorageRepository` gravar e remover registros no objeto da categoria:
`client_services_{slug}.jsonl`.

Esta tarefa **não** muda os serviços de cadastro e exclusão. Ela só muda o repositório e ajusta as
chamadas.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md` (erros do boto3 viram `ClientStorageError`)
- `.claude/code_patterns/security.md` (nunca registrar `user_code` nem o conteúdo do registro)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Trocar a constante `CLIENT_RECORDS_OBJECT_KEY` por uma montagem de chave a partir do slug, por
  exemplo `CLIENT_RECORDS_OBJECT_KEY_TEMPLATE: Final[str] = "client_services_{category}.jsonl"` e
  um método estático `_object_key(category_slug: str) -> str`.
- `save_client(registration, category_slug: str)` e `delete_client(user_code, category_slug: str)`
  passam a ler e gravar só o objeto da categoria.
- `_read_records` e `_put_records` recebem a chave do objeto como parâmetro.
- Um slug vazio é um erro de uso: lançar `ClientStorageError` antes de acessar o S3.
- O resto do comportamento não muda: substituir a linha do `user_code` (sem duplicar), objeto
  inexistente tratado como lista vazia, e reescrita só quando algo foi removido.
- Os logs passam a mostrar a chave do objeto usada (que contém só o slug).
- Atualizar a docstring do módulo e ajustar as chamadas em `RegistrationService` e
  `DeletionService` para compilar. Até as tarefas 5.0 e 6.0, um slug provisório é aceitável.
</requirements>

## Subtarefas

- [x] 4.1 Criar o template da chave e o `_object_key`.
- [x] 4.2 Adicionar `category_slug` em `save_client` e `delete_client` e repassar a chave aos métodos internos.
- [x] 4.3 Validar o slug vazio.
- [x] 4.4 Ajustar as chamadas e a docstring.
- [x] 4.5 Criar ou atualizar os testes unitários e de integração.
- [x] 4.6 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

O formato do nome do arquivo e o uso do slug estão em `tasks/divisao-categorias/tasks.md`, nas
seções "Categorias" e "Cadastro". O arquivo antigo `client_services.jsonl` não é lido nem alterado
(ver "Fora de escopo").

## Critérios de Sucesso

- `save_client(registration, "alimentacao")` grava em `client_services_alimentacao.jsonl`.
- `delete_client(user_code, "beleza")` lê e reescreve só `client_services_beleza.jsonl`.
- Clientes de categorias diferentes ficam em objetos diferentes.
- Um slug vazio lança `ClientStorageError` sem chamar o S3.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/storage/test_storage_repository.py`): a chave correta em
  `get_object` e `put_object`; o merge idempotente na categoria; a exclusão na categoria; o slug
  vazio; os erros do boto3.
- [x] Testes de integração (`tests/integration/storage/test_storage_integration.py`): seguir o
  padrão existente; gravar dois clientes em categorias diferentes e confirmar que cada objeto tem
  só o seu cliente; excluir de uma categoria sem afetar a outra.
- [x] Testes E2E: não se aplica.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/storage/repository.py`
- `app/application/registration/service.py` e `app/application/deletion/service.py` (só os ajustes das chamadas)
- `tests/unit/storage/test_storage_repository.py`
- `tests/integration/storage/test_storage_integration.py`
