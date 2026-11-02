# Resumo de Tarefas de Implementação dos Modelos de Embedding Configuráveis

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../.mine/refatoracao_modelo_embedding.md` (raiz do repositório).
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md` (§1.4 e §2.2 geração de embeddings na OpenAI).
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- O modelo de embedding passa a ficar em `open_ai.models`, um objeto com N modelos nomeados
  (ex.: `economic`, `stronger`), cada um com `default: bool` e `model_embeddings: str`.
- O modelo usado é o **primeiro** encontrado com `default: true` (ordem do JSON).
- Se **nenhum** modelo tiver `default: true`, a aplicação **falha ao iniciar** com erro de configuração claro.
- Alteração aplicada nas chaves `dev` e `prod` de `env.json` e `env.example.json`.

## Fora de escopo (ponto de atenção)

- **Compatibilidade com a dimensão do Pinecone:** o índice usa `dimension: 1536`. O
  `text-embedding-3-large` gera vetores de 3072 dimensões; torná-lo default exige um índice novo e
  a regeração dos embeddings existentes. Trocar de modelo, mesmo com a mesma dimensão, também
  invalida os vetores já gravados (espaços vetoriais diferentes). Nenhuma validação automática será feita.

## Tarefas

- [x] 1.0 Nova estrutura de configuração dos modelos de embedding
- [x] 2.0 `OpenAIService` passa a usar o modelo default resolvido
