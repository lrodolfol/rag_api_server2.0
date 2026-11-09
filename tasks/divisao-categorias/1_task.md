# Tarefa 1.0: Catálogo de categorias (domínio, configuração, Redis e carga no startup)

<critical>Ler os arquivos `divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje não existe o conceito de categoria no sistema. Esta tarefa cria a base que todas as outras
usam:

- um modelo de domínio `Category`, com nome e slug;
- a lista inicial de categorias e a chave do Redis no arquivo de configuração;
- um repositório Redis para ler e adicionar categorias;
- um serviço de aplicação que resolve um nome qualquer para uma categoria do catálogo;
- a carga da lista inicial no Redis quando a aplicação sobe.

Esta tarefa **não** muda o cadastro, a exclusão nem a busca.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (domínio sem dependência de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, constantes `Final`, métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha do Redis registrada, nunca engolida em silêncio)
- `.claude/code_patterns/security.md` (nada sensível no código)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- **Domínio** (`app/domain/category.py`, exportado em `app/domain/__init__.py`):
  - modelo tipado `Category` com `name: str` (sem espaços nas pontas e em maiúsculas) e
    `slug: str`, criado por um construtor como `Category.from_name(name)`;
  - o slug remove acentos (`unicodedata`), deixa tudo minúsculo, troca espaços por `_` e remove
    o que não for letra, número ou `_`. Exemplo: `"SERVIÇOS PROFISSIONAIS"` → `servicos_profissionais`;
  - um nome vazio ou só com espaços é inválido (lançar uma exceção de domínio ou validação do
    Pydantic, como já é feito nos outros modelos do domínio);
  - usar só a biblioteca padrão e o Pydantic. O domínio não importa nada da infraestrutura.
- **Configuração** (`app/infrastructure/config/models.py`):
  - novo `CategoriesConfig` com `redis_key: str`, `initial: list[str]` e `fallback: str`, todos
    obrigatórios e não vazios;
  - campo `categories: CategoriesConfig` em `AppConfig`;
  - preencher `env.json` e `env.example.json` com as 20 categorias de `divisao_em_categorias.md`,
    a chave (por exemplo `"knowledge_categories"`) e o `fallback` `"OUTROS"`.
- **Repositório Redis** (`app/infrastructure/redis/category_repository.py`, exportado no pacote):
  - `RedisCategoryRepository(client: Redis, config: CategoriesConfig)`;
  - `async get_all() -> list[str]`: lê o SET (`SMEMBERS`) e devolve os nomes em ordem alfabética.
    Em `RedisError`, registra com `logger.exception` e devolve `[]`;
  - `async add(name: str) -> None`: `SADD` de um nome. Em `RedisError`, registra e segue;
  - `async seed(names: list[str]) -> None`: `SADD` de todos os nomes de uma vez. Em `RedisError`,
    registra e segue.
- **Serviço de aplicação** (`app/application/categories/service.py`, com `__init__.py`):
  - `CategoryService(repository: RedisCategoryRepository, config: CategoriesConfig)`;
  - `async list_names() -> list[str]`: repassa `get_all()`;
  - `async find(name: str) -> Category | None`: procura no catálogo, comparando pelo slug. Não
    adiciona nada. Será usado pela busca (tarefa 7.0);
  - `async resolve_or_create(name: str) -> Category`: igual a `find`, mas se a categoria não
    existir, adiciona ao Redis. Se `name` estiver vazio, usa o `fallback` da configuração. Será
    usado pelo cadastro (tarefa 5.0);
  - registrar em log quando uma categoria nova for criada (só o nome da categoria).
- **Startup** (`app/main.py` e `app/api/dependencies.py`):
  - criar as fábricas do repositório e do serviço em `dependencies.py`, reaproveitando o
    `_redis_client()` existente;
  - no `lifespan`, chamar `seed` com `config.categories.initial`. Uma falha do Redis não impede a
    aplicação de subir.
</requirements>

## Subtarefas

- [x] 1.1 Criar o modelo `Category` e a geração do slug no domínio e exportá-los.
- [x] 1.2 Criar o `CategoriesConfig`, adicioná-lo ao `AppConfig` e atualizar `env.json` e `env.example.json`.
- [x] 1.3 Criar o `RedisCategoryRepository` (`get_all`, `add` e `seed`).
- [x] 1.4 Criar o `CategoryService` (`list_names`, `find` e `resolve_or_create`).
- [x] 1.5 Criar as fábricas em `dependencies.py` e a carga inicial no `lifespan`.
- [x] 1.6 Criar os testes unitários e de integração.
- [x] 1.7 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

As regras de nome x slug, da chave do Redis e do `fallback` estão em
`tasks/divisao-categorias/tasks.md`, na seção "Categorias". Para o padrão do repositório Redis
(cliente injetado, `RedisError` registrado), siga `app/infrastructure/redis/answer_cache_repository.py`.
Para o carregamento da configuração, siga os outros modelos de `app/infrastructure/config/models.py`.

## Critérios de Sucesso

- `Category.from_name("Serviços Profissionais")` gera nome `SERVIÇOS PROFISSIONAIS` e slug
  `servicos_profissionais`. `ALIMENTAÇÃO` gera `alimentacao` e `CASA E MANUTENÇÃO` gera
  `casa_e_manutencao`.
- `find("alimentacao")` encontra `ALIMENTAÇÃO`. `find("inexistente")` retorna `None` e não grava
  no Redis.
- `resolve_or_create("PETSHOP")` grava `PETSHOP` no Redis e retorna a categoria.
  `resolve_or_create("")` retorna a categoria `fallback`.
- Com o Redis fora do ar, a aplicação sobe e `get_all()` retorna `[]`, com o erro registrado.
- Nenhuma categoria está escrita no código Python.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/domain/test_category.py`: casos parametrizados do slug (acentos, espaços,
    maiúsculas e minúsculas, espaços nas pontas) e nome vazio inválido;
  - `tests/unit/redis/test_category_repository.py`: `get_all` ordenado, `add`, `seed` e
    `RedisError` em cada um, com o cliente Redis mockado;
  - `tests/unit/categories/test_category_service.py`: `find` com e sem match, `resolve_or_create`
    com categoria existente, nova e vazia, com o repositório mockado;
  - `tests/unit/config/`: o `CategoriesConfig` valida campos obrigatórios e listas vazias.
- [x] Testes de integração:
  - `tests/integration/redis/test_category_integration.py`: `seed` duas vezes não duplica,
    `add` e `get_all` (seguir o padrão dos testes de integração de Redis existentes);
  - `tests/integration/config/`: o `env.example.json` carrega as 20 categorias.
- [x] Testes E2E: não se aplica.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/category.py` (novo) e `app/domain/__init__.py`
- `app/infrastructure/config/models.py`, `env.json` e `env.example.json`
- `app/infrastructure/redis/category_repository.py` (novo) e `app/infrastructure/redis/__init__.py`
- `app/application/categories/__init__.py` e `app/application/categories/service.py` (novos)
- `app/api/dependencies.py` e `app/main.py`
- `tests/unit/domain/`, `tests/unit/redis/`, `tests/unit/categories/`, `tests/unit/config/`
- `tests/integration/redis/` e `tests/integration/config/`
