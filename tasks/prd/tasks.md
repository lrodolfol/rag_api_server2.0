# Resumo de Tarefas de Implementação da API RAG

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes. Detalhes de implementação estão
em `tasks/techspec.md` e `tasks/prd.md` — os arquivos de tarefa apenas referenciam.

## Tarefas

- [x] 1.0 Fundação de Configuração (settings tipado + `env.json` + variáveis de ambiente)
- [x] 2.0 Modelos de Domínio e Exceções
- [x] 3.0 Serviço de Integração OpenAI (moderação, embeddings, chat)
- [x] 4.0 Serviço de Processamento de Texto (normalização + chunking LangChain)
- [x] 5.0 Repositório de Vetores Pinecone (índice, upsert, delete, query com similaridade > 0.9)
- [x] 6.0 Serviço de Armazenamento em Bucket S3 (JSONL)
- [x] 7.0 Histórico no Redis + Rate Limiter em memória
- [x] 8.0 Funcionalidade de Cadastro de Empresa (ingestão + endpoint)
- [x] 9.0 Funcionalidade de Busca (serviço compartilhado + endpoints WhatsApp e chat online)
- [x] 10.0 Integração da Aplicação e Tratamento de Erros (DI, rotas, exception handlers, E2E)
