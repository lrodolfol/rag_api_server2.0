# Tarefa 3.0: Categoria nos vetores do Pinecone (metadado, filtro e leitura por `user_code`)

<critical>Ler os arquivos `../../meus_prompts/divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje cada vetor tem só os metadados `text` e `user_code`, e a busca consulta o índice inteiro.
Esta tarefa prepara o `PineconeVectorRepository` para:

- gravar o slug da categoria no metadado `category`;
- filtrar a busca por categoria (filtro opcional);
- descobrir a categoria atual de um cliente pelo `user_code`.

Esta tarefa **não** muda os serviços de cadastro, exclusão e busca.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md` (erros do SDK viram `VectorRepositoryError`)
- `.claude/code_patterns/security.md` (nunca registrar `user_code`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `upsert_company_vectors(company_name, user_code, category_slug, embeddings)`: o novo parâmetro
  `category_slug: str` vai para o metadado `category` de cada vetor, em `_build_vectors`.
- `query(embedding, top_k=DEFAULT_TOP_K, category_slug: str | None = None)`:
  - com `category_slug`, a consulta usa `filter={"category": {"$eq": category_slug}}`;
  - sem `category_slug` (`None`), o comportamento é o de hoje, sem filtro;
  - o limiar de similaridade e o `_filter_matches` não mudam.
- Novo método `async get_category_by_user_code(user_code: str) -> str | None`:
  - mesma estratégia de `has_vectors_for_user_code` (vetor de sonda e filtro por `user_code`),
    mas com `include_metadata=True`;
  - retorna o valor de `category` do primeiro match, ou `None` quando não há vetores ou quando o
    vetor não tem `category` (dado antigo);
  - `NotFoundException` resulta em `None`. As outras falhas do SDK viram `VectorRepositoryError`.
  - Reaproveite a montagem da sonda para não duplicar código com `_has_vectors_sync`.
- Adicionar `category: str = ""` ao `VectorMatch` (`app/infrastructure/pinecone/models.py`) e
  preenchê-lo em `_filter_matches`.
- Atualizar as chamadas existentes para compilar. Até as tarefas 5.0 e 7.0, o cadastro pode passar
  um slug provisório e a busca continua sem filtro.
- Registrar em log se a consulta usou filtro e qual slug (nunca o `user_code`).
</requirements>

## Subtarefas

- [x] 3.1 Adicionar o metadado `category` no upsert.
- [x] 3.2 Adicionar o filtro opcional `category_slug` em `query`.
- [x] 3.3 Criar `get_category_by_user_code`, reaproveitando a lógica da sonda.
- [x] 3.4 Adicionar `category` ao `VectorMatch`.
- [x] 3.5 Ajustar as chamadas existentes.
- [x] 3.6 Criar ou atualizar os testes unitários e de integração.
- [x] 3.7 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

A decisão de usar metadado com filtro (e não um namespace por categoria) está em
`tasks/divisao-categorias/tasks.md`, nas seções "Regras de negócio decididas" e "Busca". Como o
índice continua o mesmo, `delete_by_user_code` e `has_vectors_for_user_code` não mudam.

## Critérios de Sucesso

- Os vetores gravados têm `{"text", "user_code", "category"}` nos metadados.
- `query(..., category_slug="alimentacao")` envia o filtro `$eq` correto.
  `query(...)` sem categoria não envia filtro.
- `get_category_by_user_code` retorna o slug gravado, ou `None` sem vetores ou sem metadado.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/pinecone/test_repository.py`): metadados do upsert; query
  com e sem filtro; `get_category_by_user_code` com match, sem match, sem metadado,
  `NotFoundException` e `PineconeException`; `VectorMatch.category` preenchido.
- [x] Testes de integração (`tests/integration/pinecone/test_pinecone_integration.py`): seguir o
  padrão existente; gravar vetores com categoria, consultar filtrando por ela e por outra categoria,
  e ler a categoria pelo `user_code`.
- [x] Testes E2E: não se aplica.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/pinecone/repository.py`
- `app/infrastructure/pinecone/models.py`
- `app/application/registration/service.py` e `app/application/search/service.py` (só os ajustes das chamadas)
- `tests/unit/pinecone/test_repository.py`
- `tests/integration/pinecone/test_pinecone_integration.py`
