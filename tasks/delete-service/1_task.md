# Tarefa 1.0: Pinecone — verificação de existência e exclusão por `user_code`

<critical>Ler os arquivos `delete-service.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O fluxo de exclusão precisa saber **se** um `user_code` tem vetores no Pinecone antes de excluir.
O repositório `PineconeVectorRepository` já tem `delete_by_user_code`, mas não tem uma forma de
verificar a existência. Esta tarefa adiciona essa verificação e deixa a exclusão robusta.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (infraestrutura isolada da regra de negócio)
- `.claude/code_patterns/python-conventions.md` (tipagem, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (traduzir erros do SDK para erro de domínio)
- `.claude/code_patterns/security.md` (nunca logar `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo método assíncrono `has_vectors_for_user_code(user_code: str) -> bool` em `PineconeVectorRepository`.
- A verificação deve usar **filtro de metadata** `{"user_code": user_code}` com `top_k=1`
  (os IDs têm formato `{empresa}-{user_code}-{i}`, então **não** é possível listar por prefixo de `user_code`).
  Como a query do Pinecone exige um vetor, usar um vetor neutro com a `dimension` vinda do `PineconeConfig` (nada hardcoded).
- A verificação **não** deve aplicar o `SIMILARITY_THRESHOLD` (basta existir pelo menos um match).
- `delete_by_user_code` deve tratar `NotFoundException` como "nada para excluir" (mesmo padrão já usado em `_replace_vectors_sync`), com log em nível warning **sem** o `user_code`.
- Chamadas síncronas do SDK sempre via `asyncio.to_thread` (padrão existente).
- Qualquer `PineconeException` deve virar `VectorRepositoryError` com mensagem segura.
- Não alterar o comportamento de `upsert_company_vectors` nem de `query`.
</requirements>

## Subtarefas

- [x] 1.1 Implementar `has_vectors_for_user_code` (método público async + helper `_sync` privado).
- [x] 1.2 Ajustar `_delete_sync` para tolerar `NotFoundException`.
- [x] 1.3 Testes de unidade em `tests/unit/pinecone/test_repository.py`:
  - retorna `True` quando a query com filtro tem match;
  - retorna `False` quando não há matches;
  - a query é feita com `filter={"user_code": ...}`, `top_k=1` e vetor com a dimensão configurada;
  - `PineconeException` vira `VectorRepositoryError` (verificação e exclusão);
  - `NotFoundException` na exclusão não levanta erro.
- [x] 1.4 Testes de integração em `tests/integration/pinecone/test_pinecone_integration.py`
  cobrindo o fluxo verificar → excluir com o client fake/mock usado no arquivo.

## Detalhes de Implementação

- Ver `tasks/techspec.md` §1.6 (exemplo de delete por filtro `user_code` e criação de índice).
- Código atual: `app/infrastructure/pinecone/repository.py` (`delete_by_user_code`, `_delete_sync`, `_query_sync`, `_replace_vectors_sync`).
- Reutilizar `create_index_if_not_exists` antes da verificação, como os outros métodos públicos fazem.

## Critérios de Sucesso

- `has_vectors_for_user_code` retorna o booleano correto nos dois cenários.
- Exclusão de um `user_code` inexistente não quebra o fluxo.
- Nenhum log contém `user_code`.
- Testes, linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (não aplicável nesta tarefa)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/pinecone/repository.py`
- `app/infrastructure/config/models.py` (`PineconeConfig.dimension`)
- `tests/unit/pinecone/test_repository.py`
- `tests/integration/pinecone/test_pinecone_integration.py`
