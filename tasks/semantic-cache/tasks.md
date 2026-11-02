# Resumo de Tarefas de Implementação do Cache Semântico (PGVECTOR)

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../.mine/cache_semantico.md` (raiz do repositório).
**Contexto técnico geral:** `tasks/prd.md` (seção "Busca de informações") e `tasks/techspec.md`
(itens 2 e 3 — fluxo de busca WhatsApp e chat online).
**Cache exato já existente:** `tasks/cache/tasks.md` (regras do fingerprint e do Redis).
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- **O cache semântico só é consultado quando o cache exato (Redis) dá miss.** Hit exato retorna
  direto, sem gerar embedding e sem consultar o PostgreSQL.
- **Normalização e fingerprint** reaproveitam `normalize_question_finger_print` e
  `build_fingerprint` de `app/application/cache/fingerprint.py`, **sem alterá-las**.
- **Embedding:** gerado **uma única vez** por requisição com a função existente
  `OpenAIService.generate_embedding_for_question`, a partir da pergunta **normalizada**, com o
  modelo default (`OpenAIConfig.default_model_embeddings`). O mesmo vetor é usado na consulta ao
  PostgreSQL, na busca do Pinecone (em miss semântico) e na gravação no cache semântico.
- **Mudança de comportamento:** o Pinecone passa a receber o embedding da pergunta normalizada.
- **Consulta:** SQL exatamente como em `../../.mine/cache_semantico.md` (seção 1.4), todos os valores
  parametrizados; `top_k` vem de `semantic_cache.top_k`; o filtro usa `prompt_version`,
  `rules_version` e `model_capability` do `FingerPrintConfig`. O vetor é enviado como texto
  (`'[0.1,0.2,...]'`) e convertido com `::vector` — **sem** a biblioteca Python `pgvector`.
- **Hit semântico** = a consulta retornou pelo menos uma linha (**sem limiar de similaridade**
  nesta versão). Usa o primeiro resultado (`best_match`):
  1. retorna a resposta armazenada (sem RAG e sem LLM);
  2. grava pergunta e resposta no histórico do usuário;
  3. grava a resposta no Redis com a chave do fingerprint da pergunta atual.
- **Miss semântico:** fluxo normal de RAG + LLM; a resposta é gravada no Redis **e** no
  PostgreSQL (somente após a resposta da LLM).
- **Não são gravadas** (Redis nem PostgreSQL): respostas vazias e `PATTERN_RESPONSE`.
- **Registro gravado:** `id` (uuid4), `prompt_version`, `rules_version`, `model_capability`,
  `input_text` (pergunta original), `normalized_text`, `response_json` (texto da resposta
  serializado como string JSON), `embedding`, `created_at`.
- **Falhas do PostgreSQL** (conexão, consulta ou gravação): log + tratadas como miss / ignoradas.
  Nunca derrubam a requisição. Falha ao gerar embedding mantém o `OpenIaException` atual.
- **Logs:** somente hit, miss, gravação e falhas, com no máximo um prefixo curto (8 caracteres)
  da chave do fingerprint. **Nunca** o texto da pergunta, a resposta ou dados sensíveis.
- **Conexão:** `psycopg.AsyncConnection` aberta e fechada por operação (`async with`). Sem pool
  (evita a dependência extra `psycopg_pool`).
- **Configuração:** host, porta, database, usuário, tabela e `top_k` em `env.json` /
  `env.example.json`; somente a senha vem de `DATA_BASE_PASSWORD`, que passa a ser obrigatória
  na inicialização (igual às outras credenciais).
- **Camadas:** o `SearchService` conversa com um serviço de aplicação (`SemanticCacheService`),
  que conversa com o repositório de infraestrutura. Só o repositório conhece SQL e `psycopg`.

## Fora de escopo (ponto de atenção)

- Limiar mínimo de similaridade: como não há limiar, toda pergunta com fingerprint compatível
  e tabela não vazia será hit semântico. Será tratado em tarefa futura.
- Expiração/limpeza da tabela `rag_response_cache` (cresce sem limite nesta versão).
- Criação ou migração da tabela (já executada no banco).
- Troca do modelo default para outra dimensão (ex.: 3072) torna a coluna `VECTOR(1536)`
  incompatível; consulta e gravação falham e são tratadas como miss.

## Tarefas

- [x] 1.0 Configuração do PostgreSQL e do cache semântico
- [x] 2.0 Repositório do cache semântico no PostgreSQL
- [x] 3.0 Embedding gerado uma única vez por requisição
- [x] 4.0 Cache semântico no fluxo de busca e injeção de dependências
