# Tarefa 2.0: S3 — remoção do registro do cliente no JSONL

<critical>Ler os arquivos `delete-service.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Os clientes ficam salvos como linhas de um único objeto JSONL (`client_services.jsonl`) no bucket S3,
via `ClientStorageRepository`. Hoje o repositório só sabe criar/atualizar (`save_client`).
Esta tarefa adiciona a remoção do registro de um `user_code`.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md` (tipagem, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/security.md` (nunca logar `user_code` nem o conteúdo dos registros)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo método assíncrono `delete_client(user_code: str) -> None` em `ClientStorageRepository`.
- Fluxo: ler os registros (reutilizar `_read_records`) → remover as linhas cujo `user_code` seja igual → regravar (reutilizar `_serialize` e `_put_records`).
- Se o objeto não existir, ou se nenhuma linha corresponder ao `user_code`, **não regravar** o arquivo (apenas log informativo).
- Se, após a remoção, não sobrar nenhum registro, gravar um objeto vazio (sem gerar uma linha `"\n"` inválida) — tratar esse caso no serializer ou no método.
- Chamadas boto3 sempre via `asyncio.to_thread`.
- Erros do boto (`BotoCoreError`, `ClientError`) viram `ClientStorageError` (padrão existente).
- Não alterar o comportamento de `save_client`.
</requirements>

## Subtarefas

- [x] 2.1 Extrair um helper estático de filtro (ex.: `_remove_record`) reaproveitável pela lógica de `_merge_record`, sem duplicar código.
- [x] 2.2 Implementar `delete_client`.
- [x] 2.3 Testes de unidade em `tests/unit/storage/test_storage_repository.py`:
  - remove apenas a linha do `user_code` informado e mantém as demais;
  - não chama `put_object` quando o `user_code` não existe;
  - não chama `put_object` quando o objeto não existe (`NoSuchKey`);
  - remover o último registro gera um corpo vazio válido;
  - erro do boto vira `ClientStorageError`.
- [x] 2.4 Testes de integração em `tests/integration/storage/test_storage_integration.py`
  cobrindo o ciclo salvar → excluir → ler.

## Detalhes de Implementação

- Ver `tasks/techspec.md` §1.5 (bucket e formato JSONL).
- Código atual: `app/infrastructure/storage/repository.py` (`save_client`, `_read_records`, `_put_records`, `_merge_record`, `_serialize`).

## Critérios de Sucesso

- O registro do cliente some do JSONL e os demais continuam intactos.
- Operação idempotente: excluir duas vezes não gera erro nem regravação desnecessária.
- Nenhum log contém `user_code` ou dados do cliente.
- Testes, linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (não aplicável nesta tarefa)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/storage/repository.py`
- `tests/unit/storage/test_storage_repository.py`
- `tests/integration/storage/test_storage_integration.py`
