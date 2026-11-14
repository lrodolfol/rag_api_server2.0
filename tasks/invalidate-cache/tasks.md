# Resumo de Tarefas de Implementação da Invalidação do Cache Semântico por Categoria

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../meus_prompts/invalid-cache-on-new-service.md` (raiz do repositório).
**Cache semântico existente:** `.mine/cache_semantico.md` (raiz), `tasks/semantic-cache/tasks.md`
e `tasks/semantic-cache-threshold/tasks.md` (regras de negócio do fluxo atual).
**Categorias, cadastro e exclusão:** `tasks/divisao-categorias/tasks.md` e
`tasks/delete-service/tasks.md`.
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Situação atual (por que a tarefa não é só um DELETE)

- A coluna `category` **já existe** na tabela `rag_response_cache` (criada manualmente pelo
  autor; nenhum script de banco faz parte desta feature). Hoje **nenhum código grava** essa
  coluna: o `INSERT` de `PostgresSemanticCacheRepository` não a inclui, então todas as linhas
  existentes estão com `category = NULL`.
- No `SearchService`, a categoria da pergunta é obtida em `_classify_question` (dentro de
  `_run_pipeline`) e descartada depois da consulta ao Pinecone. `_store_answer` não a recebe.
- Portanto a feature tem dois lados: **gravar** a categoria da pergunta em cada entrada do cache
  semântico (tarefas 1.0 a 3.0) e **apagar** as entradas da categoria afetada quando um serviço
  é cadastrado, atualizado ou excluído (tarefas 4.0 e 5.0).

## Regras de negócio decididas

- **Valor da coluna `category`:** o **slug** da categoria (ex.: `alimentacao`), o mesmo
  identificador já usado no metadado `category` do Pinecone e no nome do arquivo do bucket.
  Nunca o nome de exibição (`ALIMENTAÇÃO`).
- **Categoria da entrada do cache semântico** = categoria em que a pergunta foi classificada
  (`SearchService._classify_question`). Quando a busca rodou **sem filtro** (catálogo vazio,
  classificação falhou ou LLM devolveu categoria desconhecida), a entrada é gravada com
  `category = NULL`, porque a resposta pode conter serviços de qualquer categoria.
- **Invalidação por categoria:** um único `DELETE` parametrizado
  `DELETE FROM {table} WHERE category IS NULL OR category = %(category)s`.
  Apaga as entradas da categoria informada **e** todas as entradas sem categoria (`NULL`), que
  podem conter o serviço alterado. Com `category = None` (cliente legado, ver abaixo) a
  comparação `category = NULL` é falsa em SQL e só as linhas `NULL` são apagadas — mesma query,
  sem ramificação.
- **Quando invalidar:**
  - **Cadastro/atualização** (`RegistrationService.register`): imediatamente **depois** do
    `upsert_company_vectors` no Pinecone, invalidar a categoria nova. Se a categoria anterior
    (`previous_slug`) existir e for diferente da nova, invalidar também a anterior (o serviço
    saiu dela). A invalidação acontece antes de `delete_client`/`save_client` no bucket, porque
    o bucket não é usado pela busca: se o bucket falhar com 500, o cache já estará coerente com
    o Pinecone.
  - **Exclusão** (`DeletionService.delete`): imediatamente **depois** do `delete_by_user_code`
    no Pinecone, invalidar a categoria lida dos vetores (`category_slug`). Cliente legado sem
    categoria (`None`) invalida somente as linhas `NULL`. Cliente sem vetores: nada é feito
    (nem no cache).
- **Falhas do PostgreSQL** na invalidação: log (`logger.exception`) e seguir o fluxo. O
  cadastro e a exclusão continuam respondendo sucesso, no mesmo padrão de `find_nearest` e
  `save` (o cache é otimização e nunca derruba a requisição).
- **Camadas:** `RegistrationService` e `DeletionService` falam só com `SemanticCacheService`
  (`invalidate_category`), que fala com `PostgresSemanticCacheRepository` (`delete_by_category`).
  Só o repositório conhece SQL e `psycopg`.
- **Logs:** registrar a categoria invalidada e a quantidade de linhas apagadas (`rowcount`).
  **Nunca** registrar `user_code`, pergunta, resposta ou embedding.
- **Contratos HTTP** (payloads e respostas de `POST /companies`, `DELETE /companies`,
  busca WhatsApp e chat online) **não mudam**.

## Fora de escopo

- **Cache exato (Redis):** continua sem invalidação por categoria (ver rascunho
  `../../meus_prompts/invalidate-cache-exato.md`). Ponto de atenção: uma pergunta idêntica dentro do TTL do Redis
  ainda recebe a resposta antiga mesmo após a invalidação do cache semântico.
- Migração das linhas antigas (`category = NULL`): elas são apagadas naturalmente na primeira
  invalidação de qualquer categoria.
- Criação ou alteração da tabela (a coluna já existe no banco).
- Invalidação por `user_code` ou por serviço específico.

## Tarefas

- [x] 1.0 Categoria na entrada do cache semântico e `delete_by_category` no repositório PostgreSQL
- [x] 2.0 `SemanticCacheService`: gravar a categoria e expor `invalidate_category`
- [x] 3.0 `SearchService` grava a categoria da pergunta no cache semântico
- [x] 4.0 Invalidação no cadastro/atualização (`RegistrationService`) e injeção de dependências
- [x] 5.0 Invalidação na exclusão (`DeletionService`), injeção de dependências e testes E2E
