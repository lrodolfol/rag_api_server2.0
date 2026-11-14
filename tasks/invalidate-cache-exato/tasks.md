# Resumo de Tarefas de Implementação da Invalidação do Cache Exato (Redis) por Categoria

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../meus_prompts/invalidate-cache-exato.md` (raiz do repositório).
**Invalidação do cache semântico (já implementada, mesmo modelo de regras):**
`tasks/invalidate-cache/tasks.md`.
**Cache exato existente:** `tasks/cache/tasks.md` e
`app/infrastructure/redis/answer_cache_repository.py`.
**Categorias, cadastro e exclusão:** `tasks/divisao-categorias/tasks.md` e
`tasks/delete-service/tasks.md`.
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Situação atual (por que a tarefa não é só um DEL)

- O cache exato grava `rag_answer_cache:<hash da fingerprint>` com TTL de 24h renovado a cada
  hit (`RedisAnswerCacheRepository`). Nenhuma chave sabe a qual categoria pertence e não existe
  índice: não há como apagar "as respostas de `alimentacao`" sem varrer o Redis.
- O cache exato é escrito em **dois** pontos do `SearchService`:
  1. `_store_answer` (pipeline RAG completo) — a categoria da pergunta já está disponível em
     `_PipelineResult.category_slug`;
  2. `_answer_from_semantic_cache` (hit no cache semântico) — a resposta é a fusão de vários
     matches, e hoje `SemanticCacheMatch` **não** traz a categoria da linha do PostgreSQL.
- Portanto a feature tem três lados: **indexar** cada chave no SET da(s) sua(s) categoria(s)
  (tarefas 1.0 a 3.0) e **apagar** as chaves do SET quando um serviço da categoria é
  cadastrado, atualizado ou excluído (tarefas 1.0 e 4.0).

## Regras de negócio decididas

- **Índice:** um SET Redis por categoria, `rag_answer_cache:category:<slug>` (ex.:
  `rag_answer_cache:category:alimentacao`), cujos membros são os hashes (`cache_key`) das
  respostas. O slug é o mesmo identificador do Pinecone e do cache semântico — nunca o nome de
  exibição (`ALIMENTAÇÃO`).
- **Respostas sem categoria** (busca sem filtro: catálogo vazio, classificação falhou ou
  categoria desconhecida; ou match semântico com `category = NULL`) vão para o SET
  `rag_answer_cache:category:__none__`, porque podem conter serviços de qualquer categoria.
- **Categoria(s) de uma chave:**
  - pipeline RAG → `{category_slug}` da classificação (`None` → `__none__`);
  - hit semântico → conjunto das categorias **dos matches aceitos** pelo threshold (os que
    entraram na fusão). A chave é adicionada ao SET de **cada** uma delas.
- **Escrita atômica:** `SET` da resposta (com TTL de 24h) e os `SADD` nos SETs de categoria
  vão numa única transação (`pipeline(transaction=True)` / MULTI-EXEC).
- **SET sem TTL:** o TTL das chaves é renovado a cada hit; se o SET expirasse antes, chaves
  vivas sairiam do índice e nunca mais seriam invalidadas. Membros cujas chaves já expiraram
  ficam no SET até a próxima invalidação da categoria (DEL de chave inexistente é inofensivo).
- **Invalidação por categoria** (`invalidate_category(category_slug: str | None)`):
  - com slug → invalida o SET do slug **e** o SET `__none__`;
  - com `None` (cliente legado sem categoria) → invalida só o SET `__none__`;
  - para cada SET: `SMEMBERS`, depois, numa transação, `DEL` das chaves de resposta e `SREM`
    **apenas dos membros lidos** (não `DEL` do SET inteiro, para não perder um `SADD`
    concorrente feito entre a leitura e a remoção). SET vazio → nada a fazer.
- **Quando invalidar:** exatamente nos mesmos pontos e com as mesmas categorias do cache
  semântico (`tasks/invalidate-cache/tasks.md`, "Quando invalidar"): cadastro/atualização
  invalida a categoria nova e, se mudou, a anterior; exclusão invalida a categoria lida dos
  vetores. Sempre logo após a escrita no Pinecone.
- **Falhas do Redis** na indexação ou invalidação: `logger.exception` e seguir o fluxo (mesmo
  padrão de `get`/`set`). Busca, cadastro e exclusão nunca falham por causa do cache.
- **Camadas:** `RegistrationService`, `DeletionService` e `SearchService` falam com
  `RedisAnswerCacheRepository` (o `SearchService` já faz isso hoje; não criar um serviço
  intermediário só para repassar chamadas). Só o repositório conhece comandos Redis.
- **Logs:** registrar a categoria invalidada e a quantidade de chaves apagadas; no máximo o
  prefixo de 8 caracteres do hash. **Nunca** `user_code`, pergunta ou resposta.
- **Contratos HTTP** (`POST /companies`, `DELETE /companies`, busca WhatsApp e chat online)
  **não mudam**.

## Fora de escopo

- **Chaves legadas** `rag_answer_cache:*` gravadas antes desta feature (sem índice): o autor
  limpará o Redis manualmente no deploy. Nenhum código de migração.
- Cache semântico (PostgreSQL): a invalidação já existe; aqui ele só passa a **devolver** a
  categoria de cada match (tarefa 2.0).
- Corrida "busca em andamento grava resposta antiga logo após a invalidação" (mesma limitação
  já aceita no cache semântico).
- Invalidação por `user_code` ou por serviço específico.

## Tarefas

- [x] 1.0 `RedisAnswerCacheRepository`: índice SET por categoria e `invalidate_category`
- [x] 2.0 `SemanticCacheMatch` passa a trazer a categoria da entrada do cache semântico
- [x] 3.0 `SearchService` indexa as respostas do cache exato pela(s) categoria(s)
- [x] 4.0 Invalidação do cache exato no cadastro/atualização e na exclusão, injeção de dependências e testes E2E
