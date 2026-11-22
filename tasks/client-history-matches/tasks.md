# Resumo de Tarefas de Implementação do Histórico de Conversas com Matches

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../meus_prompts/client_histotic_refactor.md` (raiz do repositório).
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- **Onde gravar:** somente na mensagem do **assistente** do histórico (Redis, chave por canal +
  usuário). A mensagem do usuário continua `{"role": "user", "text": "..."}`.
- **Formato:** novo campo opcional `context` em `MessageHistoryItem`, com um modelo tipado
  contendo `rag_matches: list[str]` — **lista simples de strings** (o texto de cada
  `VectorMatch`, na ordem retornada pelo Pinecone, mais relevante primeiro). Não usar o formato
  `[{"0": "...", "1": "..."}]` do documento de requisitos (decisão aprovada).
  ```json
  {
    "role": "assistant",
    "text": "O Sabor da Roça oferece refeições caseiras...",
    "context": { "rag_matches": ["Name: sabor_da_roca\n...", "..."] }
  }
  ```
- **Sem matches de RAG** (resposta vinda do cache exato ou do cache semântico, ou busca vetorial
  sem resultados): o campo `context` fica `None` e é **omitido** do JSON gravado (não grava
  `"context": null`).
- **Compatibilidade:** históricos já gravados (sem `context`) continuam sendo lidos sem erro.
- **Resposta vazia:** mantém a regra atual — a mensagem do assistente **não** é gravada,
  então os matches também não.
- **LLM:** os matches **não** são enviados ao modelo. `OpenAIService._build_history` continua
  enviando somente `role` e `text`. O objetivo desta entrega é apenas gravar o contexto para
  análise (decisão aprovada).
- **Segurança/logs:** nunca logar o conteúdo dos matches; pode-se logar a quantidade.

## Fora de escopo

- Gravar o contexto no cache exato.
- Gravar o contexto no cache semântico.
- Enviar os matches do histórico ao LLM.

## Tarefas

- [x] 1.0 Modelo de domínio com `context` opcional e serialização no Redis
- [x] 2.0 `SearchService` grava os matches do RAG no histórico
