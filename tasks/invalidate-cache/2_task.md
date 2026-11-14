# Tarefa 2.0: `SemanticCacheService`: gravar a categoria e expor `invalidate_category`

<critical>Ler os arquivos `../../meus_prompts/invalid-cache-on-new-service.md` (raiz), `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O `SemanticCacheService` (`app/application/cache/semantic_cache_service.py`) é a única porta de
entrada da camada de aplicação para o cache semântico. Esta tarefa faz `store` receber a
categoria da pergunta e repassá-la para a `SemanticCacheEntry`, e cria o método
`invalidate_category`, que os serviços de cadastro e exclusão usarão nas tarefas 4.0 e 5.0.
Depende da tarefa 1.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviço de aplicação esconde o repositório; cadastro/exclusão não conhecem SQL)
- `.claude/code_patterns/python-conventions.md` (tipagem explícita, parâmetros nomeados, métodos curtos)
- `.claude/code_patterns/error-handling.md` (o repositório já trata e loga falhas; o serviço não engole nem relança)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `store` ganha o parâmetro `category_slug: str | None` (obrigatório, nomeado após `embedding`
  ou na posição que mantiver a chamada legível) e o repassa em
  `SemanticCacheEntry(..., category=category_slug)`.
- A regra atual de `store` não muda: respostas não cacheáveis (`is_cacheable_answer`) continuam
  não sendo gravadas.
- Novo método `async def invalidate_category(self, category_slug: str | None) -> None` que
  delega para `self._repository.delete_by_category(category_slug)`. Sem lógica extra: a regra
  "categoria + linhas `NULL`" vive no SQL do repositório.
- Atualizar a docstring do módulo e da classe para descrever a invalidação por categoria.
- `find_answer` **não muda**.
- Não exportar nada novo em `app/application/cache/__init__.py` (a classe já é exportada).
</requirements>

## Subtarefas

- [x] 2.1 Adicionar `category_slug` em `store` e repassar para a entrada.
- [x] 2.2 Criar `invalidate_category` delegando ao repositório.
- [x] 2.3 Atualizar a chamada de `store` no `SearchService` para compilar/rodar (passando `None`
  temporariamente **ou** já implementando a tarefa 3.0 em seguida; o valor real vem da 3.0).
- [x] 2.4 Testes de unidade do serviço.
- [x] 2.5 Testes de integração do serviço com o banco em memória.

## Detalhes de Implementação

- Estrutura atual de `store` (id `uuid4`, `created_at` em UTC naive, `answer.to_json()`):
  `app/application/cache/semantic_cache_service.py`.
- Campo `category` e método `delete_by_category`: tarefa 1.0.
- Regras de invalidação: `tasks/invalidate-cache/tasks.md`, seção "Regras de negócio decididas".

## Critérios de Sucesso

- `store(..., category_slug="alimentacao")` chama `repository.save` com uma entrada cujo
  `category == "alimentacao"`; com `category_slug=None` a entrada tem `category is None`.
- `invalidate_category("beleza")` chama `repository.delete_by_category("beleza")` exatamente uma
  vez; `invalidate_category(None)` repassa `None`.
- Respostas sem itens continuam sem ser gravadas, independentemente da categoria.
- Todos os testes que já existiam continuam passando.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/cache/test_semantic_cache_service.py`, `AsyncMock` do
  repositório como hoje):
  - `store` grava a categoria recebida (slug e `None`);
  - `invalidate_category` delega ao repositório com o mesmo valor (slug e `None`);
  - testes existentes de `store` atualizados para o novo parâmetro.
- [x] Testes de integração (`tests/integration/postgres/test_semantic_cache_integration.py` ou
  novo `tests/integration/cache/test_semantic_cache_service_integration.py`, fixture
  `semantic_cache_db`): `store` em duas categorias + `invalidate_category` de uma delas →
  `find_answer` devolve só a outra.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/cache/semantic_cache_service.py`
- `app/application/search/service.py` (apenas a chamada de `store`, ver subtarefa 2.3)
- `tests/unit/cache/test_semantic_cache_service.py`
- `tests/integration/postgres/test_semantic_cache_integration.py`
