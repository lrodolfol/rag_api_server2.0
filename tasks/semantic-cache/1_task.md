# Tarefa 1.0: Configuração do PostgreSQL e do cache semântico

<critical>Ler os arquivos `../../.mine/cache_semantico.md` (raiz), `tasks/semantic-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O cache semântico precisa saber como se conectar ao PostgreSQL e quais parâmetros usar na
consulta (tabela e `top_k`). Esta tarefa cria as seções tipadas `postgres` e `semantic_cache`
na configuração, liga a senha à variável de ambiente `DATA_BASE_PASSWORD` e adiciona a
dependência `psycopg[binary]`. Nenhuma lógica de banco é implementada aqui; só a configuração
fica disponível e validada.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (configuração isolada na camada de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, modelos Pydantic, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (configuração inválida falha com `ConfigError` claro)
- `.claude/code_patterns/security.md` (senha como `SecretStr`, vinda somente do ambiente)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo modelo `PostgresConfig` em `app/infrastructure/config/models.py` com `host: str`,
  `port: int`, `database: str`, `user: str` e `password: SecretStr`.
- Novo modelo `SemanticCacheConfig` com `table: str` (não vazio) e `top_k: int` (maior que 0,
  ex.: `Field(gt=0)`).
- `AppConfig` ganha os campos `postgres: PostgresConfig` e `semantic_cache: SemanticCacheConfig`.
- Exportar os dois modelos em `app/infrastructure/config/__init__.py`, seguindo o padrão atual.
- Adicionar `("postgres", "password"): "DATA_BASE_PASSWORD"` em `SECRET_ENV_VARS`
  (`app/infrastructure/config/loader.py`). Nenhuma outra mudança no loader.
- Adicionar as seções `postgres` e `semantic_cache` dentro de `dev` e `prod` em `env.json`
  **e** `env.example.json`, no formato da seção "Configuração" de `cache_semantico.md`
  (a senha fica com o texto `"get from environment"`, como as outras seções).
- `.env.example`: `DATA_BASE_PASSWORD=""` e remover `DATA_BASE_HOST`. Garantir que o `.env`
  local tenha `DATA_BASE_PASSWORD` (sem commitar valor real).
- `requirements.txt`: adicionar `psycopg[binary]` com faixa de versão (ex.: `>=3.2,<4.0`).
  **Não** adicionar `pgvector` nem `psycopg_pool`.
- Instalar a dependência **dentro do `.venv`**.
- Nenhum valor de conexão fixo no código-fonte.
</requirements>

## Subtarefas

- [x] 1.1 Criar `PostgresConfig` e `SemanticCacheConfig` e adicioná-los em `AppConfig`.
- [x] 1.2 Exportar os modelos no `__init__.py` do pacote de configuração.
- [x] 1.3 Mapear `DATA_BASE_PASSWORD` em `SECRET_ENV_VARS`.
- [x] 1.4 Atualizar `env.json` e `env.example.json` (`dev` e `prod`).
- [x] 1.5 Atualizar `.env.example` (e `.env` local) e `requirements.txt`; instalar no `.venv`.
- [x] 1.6 Atualizar as fixtures de configuração dos testes existentes (ex.: `_section` em
  `tests/unit/config/test_loader.py`, `conftest.py` e qualquer fixture que monta `AppConfig` ou
  define variáveis de ambiente de segredo) para incluir as novas seções e `DATA_BASE_PASSWORD`.
- [x] 1.7 Testes de unidade dos modelos.
- [x] 1.8 Testes de integração do loader com os arquivos JSON reais.

## Detalhes de Implementação

- Siga o padrão de `RedisConfig` (senha `SecretStr`) e `FingerPrintConfig` (`Field(min_length=1)`)
  em `app/infrastructure/config/models.py`.
- O fluxo de injeção de segredos e conversão de `ValidationError` em `ConfigError` já existe em
  `app/infrastructure/config/loader.py`.
- Formato das seções e variáveis: `../../.mine/cache_semantico.md`, seção "Configuração".

## Critérios de Sucesso

- `get_config().postgres` e `get_config().semantic_cache` devolvem valores tipados em `dev` e `prod`.
- A senha nunca aparece em `repr`/logs (é `SecretStr`).
- A aplicação não sobe sem `DATA_BASE_PASSWORD`, sem as seções ou com `top_k <= 0`, com mensagem clara.
- Todos os testes que já existiam continuam passando.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/config/test_models.py` e `tests/unit/config/test_loader.py`):
  - `PostgresConfig` e `SemanticCacheConfig` válidos.
  - Falha com campo ausente, `table` vazio e `top_k` igual a 0 ou negativo.
  - `password` é mascarada no `repr`.
  - Loader injeta `DATA_BASE_PASSWORD` em `postgres.password` e falha (`ConfigError`) sem ela.
- [x] Testes de integração (`tests/integration/config/test_config_integration.py`):
  - `env.json` e `env.example.json` carregam `postgres` e `semantic_cache` em `dev` e `prod`.
  - Seção `postgres` ou `semantic_cache` removida → `ConfigError`.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/config/models.py`
- `app/infrastructure/config/__init__.py`
- `app/infrastructure/config/loader.py`
- `env.json`
- `env.example.json`
- `.env.example`
- `requirements.txt`
- `tests/unit/config/test_models.py`
- `tests/unit/config/test_loader.py`
- `tests/integration/config/test_config_integration.py`
