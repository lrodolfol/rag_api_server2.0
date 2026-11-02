# Tarefa 1.0: Configuração `finger_print`

<critical>Ler os arquivos `../../.mine/implementacao_cahce.md` (raiz), `tasks/cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O fingerprint usa três valores que mudam por ambiente e são alterados manualmente para invalidar
o cache: `prompt_version`, `rules_version` e `model_capability`. Esta tarefa cria a seção tipada
`finger_print` na configuração e a adiciona aos arquivos `env.json` e `env.example.json`. Nenhuma
lógica de cache é implementada aqui; só a configuração fica disponível e validada.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (configuração isolada na camada de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, modelos Pydantic, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (configuração inválida falha com `ConfigError` claro)
- `.claude/code_patterns/security.md` (nenhum dado sensível; seção não contém segredos)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo modelo Pydantic `FingerPrintConfig` em `app/infrastructure/config/models.py` com os campos
  `prompt_version: str`, `rules_version: str` e `model_capability: str`.
- Os três campos são obrigatórios e não podem ser vazios (ex.: `Field(min_length=1)`).
- `AppConfig` ganha o campo `finger_print: FingerPrintConfig`.
- Exportar `FingerPrintConfig` em `app/infrastructure/config/__init__.py`, seguindo o padrão dos
  outros modelos.
- Adicionar a chave `finger_print` dentro de `dev` e `prod` em `env.json` **e** `env.example.json`,
  com o formato do `implementacao_cahce.md`:
  ```json
  "finger_print": {
    "prompt_version": "1.0.0",
    "rules_version": "1.0.0",
    "model_capability": "economic"
  }
  ```
- `model_capability` é apenas uma string. **Não** validar contra `open_ai.models` (decisão
  registrada em `tasks/cache/tasks.md`).
- Não alterar `loader.py` nem `SECRET_ENV_VARS`: a seção não tem segredos.
- Configuração sem `finger_print`, ou com campo vazio, deve falhar no carregamento com
  `ConfigError`, igual às outras seções.
</requirements>

## Subtarefas

- [x] 1.1 Criar `FingerPrintConfig` e adicionar `finger_print` em `AppConfig`.
- [x] 1.2 Exportar `FingerPrintConfig` no `__init__.py` do pacote de configuração.
- [x] 1.3 Atualizar `env.json` e `env.example.json` (`dev` e `prod`).
- [x] 1.4 Atualizar as fixtures de configuração dos testes existentes (ex.: `_section` em
  `tests/unit/config/test_loader.py` e quaisquer fixtures que montam `AppConfig`) para incluir
  `finger_print`.
- [x] 1.5 Testes de unidade do modelo.
- [x] 1.6 Testes de integração do loader com os arquivos JSON reais.

## Detalhes de Implementação

- Siga o padrão de `OpenAIConfig` / `PineconeConfig` em `app/infrastructure/config/models.py`.
- O fluxo de carregamento e conversão de `ValidationError` em `ConfigError` já existe em
  `app/infrastructure/config/loader.py`; nada novo é necessário além do modelo.
- Formato e motivação da seção: `../../.mine/implementacao_cahce.md`, "Onde cada informação estará disponível?".

## Critérios de Sucesso

- `get_config().finger_print` devolve os três valores tipados para `dev` e `prod`.
- A aplicação não sobe se `finger_print` estiver ausente ou com campo vazio, e a mensagem de erro é clara.
- Todos os testes que já existiam continuam passando.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/config/test_models.py`):
  - `FingerPrintConfig` válido com os três campos.
  - Falha quando algum campo está ausente.
  - Falha quando algum campo é string vazia.
- [x] Testes de integração (`tests/integration/config/test_config_integration.py`):
  - `env.json` e `env.example.json` carregam `finger_print` em `dev` e `prod`.
  - Seção `finger_print` removida → `ConfigError`.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/config/models.py`
- `app/infrastructure/config/__init__.py`
- `app/infrastructure/config/loader.py` (apenas leitura)
- `env.json`
- `env.example.json`
- `tests/unit/config/test_models.py`
- `tests/unit/config/test_loader.py`
- `tests/integration/config/test_config_integration.py`
