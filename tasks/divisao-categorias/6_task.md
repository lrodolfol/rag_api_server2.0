# Tarefa 6.0: Integração da categoria na exclusão (`DeletionService`)

<critical>Ler os arquivos `../../meus_prompts/divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/delete-service/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Com os clientes divididos em vários arquivos, a exclusão precisa saber em qual arquivo está o
registro. Esta tarefa faz o `DeletionService` ler a categoria nos metadados do Pinecone **antes**
de apagar os vetores e então remover o registro do arquivo dessa categoria.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/security.md` (nunca registrar `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Manter a verificação atual: sem vetores para o `user_code`, nada é feito e a requisição tem
  sucesso.
- Com vetores: ler `get_category_by_user_code` → apagar os vetores → se houver categoria, chamar
  `delete_client(user_code, category_slug)`.
- Sem `category` nos vetores (dado antigo): apagar os vetores, **não** chamar o storage e
  registrar um `warning` dizendo que o registro antigo não foi removido do bucket.
- Remover o slug provisório deixado pela tarefa 4.0.
- Atualizar a docstring do módulo e o item 4 da `tasks/techspec.md`, se você estiver documentando
  o fluxo lá.
- O contrato HTTP da exclusão não muda.
</requirements>

## Subtarefas

- [x] 6.1 Ler a categoria antes de apagar os vetores.
- [x] 6.2 Remover do arquivo da categoria, com o caminho de dados antigos.
- [x] 6.3 Atualizar a docstring.
- [x] 6.4 Criar ou atualizar os testes unitários e de integração.
- [x] 6.5 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

As regras estão em `tasks/divisao-categorias/tasks.md`, na seção "Exclusão". O fluxo original de
exclusão está em `tasks/delete-service/tasks.md`.

## Critérios de Sucesso

- Cliente com vetores na categoria `beleza`: vetores apagados e registro removido de
  `client_services_beleza.jsonl`.
- Cliente sem vetores: nenhuma chamada de exclusão.
- Cliente com vetores antigos sem categoria: vetores apagados, storage não chamado e `warning`
  registrado.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/deletion/test_deletion_service.py`): os três cenários
  acima, conferindo a ordem das chamadas (categoria lida antes de apagar os vetores).
- [x] Testes de integração (`tests/integration/deletion/test_deletion_integration.py` e
  `tests/integration/api/test_deletion_api.py`): seguir o padrão existente, com a categoria
  repassada ao storage.
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`): cadastro seguido de exclusão,
  removendo o registro do arquivo da categoria.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/deletion/service.py`
- `tests/unit/deletion/test_deletion_service.py`
- `tests/integration/deletion/test_deletion_integration.py`
- `tests/integration/api/test_deletion_api.py` e `tests/integration/api/test_e2e_flows.py`
