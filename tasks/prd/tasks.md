# Resumo de Tarefas de Implementação de — API RAG (`rag-api`)

> Origem: `tasks/prd.md` e `tasks/techspec.md` (+ `tasks/fluxo_mermaid.md`).
> Padrões: `.agents/code_patterns/*` e instruções em `.agents/instructions/*`.
> Ordem: dependências antes das dependentes. Cada tarefa é um entregável incremental com testes próprios.

## Tarefas

- [x] 1.0 Fundação do projeto (arquitetura, configuração, logging, bootstrap FastAPI)
- [x] 2.0 Domínio e modelos tipados
- [ ] 3.0 Persistência PostgreSQL (categories, knowledge_base, pgvector)
- [ ] 4.0 Integração OpenAI (embeddings, chat, categorização)
- [ ] 5.0 Armazenamento em bucket
- [ ] 6.0 Histórico de mensagens com Redis (TTL 30 min)
- [ ] 7.0 Processamento de texto (normalização e geração de chunks)
- [ ] 8.0 Caso de uso: Cadastro de empresa/negócio
- [ ] 9.0 Caso de uso: Busca e resposta (RAG)
- [ ] 10.0 Endpoints da API (cadastro, WhatsApp, chat online)

## Arquivos de tarefa

| # | Arquivo | Depende de |
|---|---------|-----------|
| 1.0 | `1_task.md` | — |
| 2.0 | `2_task.md` | 1.0 |
| 3.0 | `3_task.md` | 1.0, 2.0 |
| 4.0 | `4_task.md` | 1.0, 2.0, 3.0 |
| 5.0 | `5_task.md` | 1.0 |
| 6.0 | `6_task.md` | 1.0, 2.0 |
| 7.0 | `7_task.md` | 1.0 |
| 8.0 | `8_task.md` | 2.0, 3.0, 4.0, 5.0, 7.0 |
| 9.0 | `9_task.md` | 2.0, 3.0, 4.0, 6.0 |
| 10.0 | `10_task.md` | 8.0, 9.0 |
