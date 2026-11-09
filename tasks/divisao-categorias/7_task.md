# Tarefa 7.0: Classificação da pergunta e busca filtrada (`SearchService`)

<critical>Ler os arquivos `divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/streaming-response/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje a busca consulta o índice inteiro do Pinecone. Esta tarefa faz o `SearchService` pedir à LLM
a categoria mais relevante para a pergunta e buscar no Pinecone só nessa categoria. Quando não for
possível definir a categoria, a busca continua sem filtro, como hoje.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md` (métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha da classificação registrada e com alternativa explícita)
- `.claude/code_patterns/security.md` (nunca registrar a pergunta)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- **OpenAI** (`app/infrastructure/openai/service.py`):
  - novo método `async classify_question(question: str, categories: list[str]) -> str`;
  - novo prompt constante `_CLASSIFICATION_PROMPT` (junto do `_MODERATION_PROMPT`), que informa as
    categorias e pede **exatamente uma**, escrita como está na lista, ou `""` quando nenhuma servir;
  - usar o modo JSON (`_JSON_TEXT_FORMAT`) e o formato `{"categoria": "..."}`;
  - retornar o texto da categoria sem espaços nas pontas. Um JSON inválido lança `OpenIaException`,
    igual à moderação. Reaproveite `_create_response` e `_strip_code_fence`.
- **Busca** (`app/application/search/service.py`):
  - injetar o `CategoryService` no `SearchService` e atualizar a fábrica em `dependencies.py`;
  - em `_run_pipeline`, antes de `_find_matches`, chamar um novo método privado (por exemplo
    `_classify_question`) que retorna `str | None` com o slug:
    - lista de categorias vazia → `None`, sem chamar a LLM;
    - categoria devolvida que não existe no catálogo (`CategoryService.find`) → `None`;
    - `OpenIaException` → registrar `warning` e retornar `None`;
  - repassar o slug para `self._vectors.query(embedding, category_slug=...)`. Com `None`, a
    busca é sem filtro;
  - registrar em log a categoria usada ou que a busca seguiu sem filtro.
- Não mudar a regra da mensagem curta, os caches, o histórico nem o formato das mensagens
  devolvidas ao cliente.
- Atualizar a docstring do módulo de busca com o novo passo.
</requirements>

## Subtarefas

- [x] 7.1 Criar `_CLASSIFICATION_PROMPT` e `OpenAIService.classify_question`.
- [x] 7.2 Injetar o `CategoryService` no `SearchService` e atualizar `dependencies.py`.
- [x] 7.3 Criar `_classify_question`, com as três alternativas de busca sem filtro.
- [x] 7.4 Repassar o slug para a consulta ao Pinecone e atualizar a docstring.
- [x] 7.5 Criar ou atualizar os testes unitários e de integração.
- [x] 7.6 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

As regras de classificação, da busca sem filtro e dos logs estão em
`tasks/divisao-categorias/tasks.md`, na seção "Busca". O filtro do Pinecone já existe desde a
tarefa 3.0 e a resolução da categoria (`find`) desde a tarefa 1.0.

## Critérios de Sucesso

- Pergunta "onde tem pizzaria?" com a LLM devolvendo `ALIMENTAÇÃO` → `query` chamado com
  `category_slug="alimentacao"`.
- LLM devolvendo `""`, uma categoria inexistente ou lançando `OpenIaException` → `query` chamado
  sem filtro, e a resposta ao cliente sai normalmente.
- Resposta encontrada no cache exato ou semântico → `classify_question` não é chamado.
- Mensagem curta → nenhuma chamada nova.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/openai/test_service.py`: o prompt de classificação inclui as categorias; parse
    válido, vazio e inválido;
  - `tests/unit/search/test_search_service.py`: categoria válida; categoria vazia; categoria
    inexistente; `OpenIaException`; lista vazia sem chamar a LLM; cache exato e semântico sem
    classificação.
- [x] Testes de integração:
  - `tests/integration/openai/test_openai_integration.py`: `classify_question` devolve uma
    categoria da lista para uma pergunta óbvia (seguir o padrão existente);
  - `tests/integration/api/test_search_api.py`: o fluxo SSE com a classificação mockada, nos
    caminhos com filtro e sem filtro.
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`): cadastro numa categoria seguido de
  uma pergunta classificada na mesma categoria.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/openai/service.py`
- `app/application/search/service.py`
- `app/api/dependencies.py`
- `tests/unit/openai/test_service.py` e `tests/unit/search/test_search_service.py`
- `tests/integration/openai/test_openai_integration.py`
- `tests/integration/api/test_search_api.py` e `tests/integration/api/test_e2e_flows.py`
