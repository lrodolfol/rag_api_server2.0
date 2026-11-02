# Tarefa 3.0: Repositório de cache de respostas no Redis

<critical>Ler os arquivos `../../.mine/implementacao_cahce.md` (raiz), `tasks/cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar o repositório que lê e grava respostas no Redis usando a chave gerada na tarefa 2.0, com a
política de expiração definida: TTL de 24h que se renova a cada hit. O repositório reusa o mesmo
cliente Redis do histórico e segue o padrão de `RedisHistoryRepository`. Falhas do Redis nunca
derrubam a requisição.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (acesso a Redis isolado na infraestrutura, cliente injetado)
- `.claude/code_patterns/python-conventions.md` (async, tipagem, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falhas do Redis registradas com `logger.exception`, nunca engolidas em silêncio)
- `.claude/code_patterns/security.md` (sem pergunta nem `user_code` nos logs)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Nova classe `RedisAnswerCacheRepository` em `app/infrastructure/redis/answer_cache_repository.py`,
  recebendo o cliente `redis.asyncio.Redis` por injeção (igual a `RedisHistoryRepository`).
- Constantes tipadas no módulo:
  - `ANSWER_CACHE_TTL_SECONDS: Final[int] = 24 * 60 * 60`
  - `ANSWER_CACHE_KEY_PREFIX: Final[str] = "rag_answer_cache"`
  - Chave final: `f"{ANSWER_CACHE_KEY_PREFIX}:{cache_key}"`.
- `async def get(self, cache_key: str) -> str | None`:
  - Hit: devolve a resposta e **renova o TTL para 24h** (`EXPIRE`). Pode ser feito com `GETEX`
    (`ex=`), em uma única chamada.
  - Miss: devolve `None`.
  - `RedisError`: `logger.exception(...)` e devolve `None` (tratado como miss).
- `async def set(self, cache_key: str, answer: str) -> None`:
  - Grava com TTL de 24h (`SET ... EX`).
  - `RedisError`: `logger.exception(...)` e retorna sem propagar.
- O repositório **não** decide o que é cacheável (resposta vazia, `PATTERN_RESPONSE`): essa regra
  é do serviço de aplicação (tarefa 4.0).
- Logs: `info` para hit, miss e gravação, usando só os 8 primeiros caracteres do `cache_key`.
  Nunca logar a resposta nem a pergunta.
- Exportar a classe e as constantes em `app/infrastructure/redis/__init__.py`.
</requirements>

## Subtarefas

- [x] 3.1 Criar `RedisAnswerCacheRepository` com as constantes de TTL e prefixo.
- [x] 3.2 Implementar `get` com renovação do TTL no hit.
- [x] 3.3 Implementar `set` com TTL de 24h.
- [x] 3.4 Tratar `RedisError` em `get` e `set` (fail-open + log).
- [x] 3.5 Exportar no `__init__.py` do pacote `redis`.
- [x] 3.6 Testes de unidade.
- [x] 3.7 Testes de integração.

## Detalhes de Implementação

- Padrão a seguir: `app/infrastructure/redis/repository.py` (`RedisHistoryRepository`): cliente
  injetado, constante de TTL, `logger.exception` em `RedisError`.
- O cliente é criado por `create_redis_client` (`app/infrastructure/redis/client.py`) com
  `decode_responses=True`, então os valores já chegam como `str`.
- Regras de TTL e falhas: `tasks/cache/tasks.md`, "Regras de negócio decididas".

## Critérios de Sucesso

- `set` seguido de `get` devolve a mesma resposta.
- Depois de `set`, o TTL da chave está em ~24h. Depois de um `get` (hit), o TTL volta para ~24h.
- Chave inexistente → `None`, sem criar a chave.
- Redis indisponível → `get` devolve `None` e `set` não lança exceção. Os dois geram log de erro.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/redis/test_answer_cache_repository.py`, com `FakeAsyncRedis`
  e `AsyncMock`, como em `tests/unit/redis/test_history_repository.py`):
  - Miss devolve `None`.
  - `set` grava no prefixo correto com TTL de 24h.
  - Hit devolve o valor e renova o TTL (reduzir o TTL manualmente antes do `get` e verificar que voltou a ~24h).
  - `RedisError` no `get` → `None`; `RedisError` no `set` → sem exceção.
  - Os logs não contêm a resposta (verificar com `caplog`).
- [x] Testes de integração (`tests/integration/redis/test_answer_cache_integration.py`, seguindo
  `tests/integration/redis/test_history_integration.py`):
  - Ciclo `set` → `get` → TTL renovado, com o cliente montado pela factory de configuração.
  - Chave expirada (TTL curto forçado no teste) → `get` devolve `None`.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/redis/answer_cache_repository.py` (novo)
- `app/infrastructure/redis/__init__.py`
- `app/infrastructure/redis/repository.py` (referência de padrão)
- `app/infrastructure/redis/client.py` (apenas leitura)
- `tests/unit/redis/test_answer_cache_repository.py` (novo)
- `tests/integration/redis/test_answer_cache_integration.py` (novo)
