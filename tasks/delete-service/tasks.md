# Resumo de Tarefas de Implementação da Exclusão de Serviços

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `delete-service.md` (raiz do repositório).
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md` (§1.5 bucket S3 e §1.6 delete no Pinecone).
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- `DELETE /companies` com body `{"user_code": "..."}`.
- Se o `user_code` **tiver** vetores no Pinecone: excluir os vetores e o registro do cliente no S3.
- Se **não tiver** vetores no Pinecone: não fazer nada (nem no Pinecone, nem no S3).
- Em ambos os casos de sucesso: HTTP 200 no envelope `ApiResponse`.
- Erro do cliente (body inválido) → 4xx; erro interno → 5xx (handlers globais já existentes).

## Tarefas

- [x] 1.0 Pinecone: verificação de existência e exclusão por `user_code`
- [x] 2.0 S3: remoção do registro do cliente no JSONL
- [x] 3.0 Serviço de aplicação de exclusão (`DeletionService`)
- [x] 4.0 Endpoint `DELETE /companies` (rota, injeção de dependências, testes E2E)
