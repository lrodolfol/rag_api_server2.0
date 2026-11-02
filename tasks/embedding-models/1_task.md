# Tarefa 1.0: Nova estrutura de configuração dos modelos de embedding

<critical>Ler os arquivos `../../.mine/refatoracao_modelo_embedding.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje `OpenAIConfig` tem um único campo `model_embeddings: str`. Esta tarefa troca esse campo por
um objeto `models` com vários modelos nomeados e adiciona a resolução do modelo default (o primeiro
com `default: true`). A configuração deve ser validada no carregamento: sem modelo default, a
aplicação não sobe.

<skills>
### Conformidade com Skills Padrões

- `../../.claude/code_patterns/architecture.md` (configuração isolada na camada de infraestrutura)
- `../../.claude/code_patterns/python-conventions.md` (tipagem, modelos Pydantic, métodos < 30 linhas)
- `../../.claude/code_patterns/error-handling.md` (erro de configuração claro, sem engolir exceções)
- `../../.claude/code_patterns/security.md` (nada sensível hardcoded; `api_key` continua vindo do ambiente)
- `../../.claude/code_patterns/testing.md`
</skills>

<requirements>
- Novo modelo Pydantic `EmbeddingModelConfig` com `default: bool` e `model_embeddings: str`
  em `app/infrastructure/config/models.py`.
- `OpenAIConfig` substitui `model_embeddings: str` por `models: dict[str, EmbeddingModelConfig]`.
- `OpenAIConfig` expõe o nome do modelo default resolvido (ex.: propriedade tipada
  `default_model_embeddings -> str`) retornando o **primeiro** modelo com `default: true`
  (respeitando a ordem do JSON — `dict` preserva a ordem de inserção).
- Validação no carregamento (ex.: `model_validator` do Pydantic): se nenhum modelo tiver
  `default: true`, falhar com mensagem clara. O erro deve chegar como `ConfigError`, seguindo o
  padrão já usado pelo `loader.py` para configuração inválida.
- Atualizar `env.json` (chave `prod`) e `env.example.json` (chaves `dev` e `prod`) para o formato
  descrito em `refatoracao_modelo_embedding.md`. A chave `dev` do `env.json` já está no formato novo.
- **Atenção em `prod`:** hoje o `env.json` de `prod` usa `text-embedding-ada-002`. Manter esse
  valor como o modelo `default: true` de `prod`, para não invalidar os vetores já gravados no
  Pinecone (ver "Fora de escopo" em `tasks.md`). Confirmar com o responsável antes de trocar.
- Não alterar `api_key`, `model_chat`, nem a resolução de segredos do `loader.py`
  (`SECRET_ENV_VARS` continua apontando para `("open_ai", "api_key")`).
</requirements>

## Subtarefas

- [x] 1.1 Criar `EmbeddingModelConfig` e trocar o campo em `OpenAIConfig` por `models`.
- [x] 1.2 Implementar a resolução do modelo default e a validação "pelo menos um default".
- [x] 1.3 Atualizar `../../env.json` (`prod`) e `env.example.json` (`dev` e `prod`).
- [x] 1.4 Atualizar a fixture `_section` de `../../tests/unit/config/test_loader.py` para o formato novo.
- [x] 1.5 Testes de unidade da resolução e da validação.
- [x] 1.6 Testes de integração do loader com os arquivos JSON reais.

## Detalhes de Implementação

- Estrutura do JSON: ver seção "Tarefa" de `../../.mine/refatoracao_modelo_embedding.md`.
- Papel do modelo de embedding no fluxo: `../techspec.md` §1.4 e §2.2.
- Após esta tarefa, `../../app/infrastructure/openai/service.py` ainda referencia
  `model_embeddings`; a troca é feita na Tarefa 2.0. Para manter a aplicação funcional entre as
  tarefas, execute a 2.0 logo em seguida (não faça merge só com a 1.0).

## Critérios de Sucesso

- A config de `dev` e `prod` carrega com sucesso a partir de `../../env.json` e `env.example.json`.
- `config.open_ai.default_model_embeddings` retorna o primeiro modelo com `default: true`.
- Config sem nenhum `default: true` gera `ConfigError` com mensagem clara.
- Lint e type checking configurados passam sem erros.

## Testes da Tarefa

- [x] Testes de unidade (`../../tests/unit/config`):
  - retorna o modelo com `default: true` quando há apenas um;
  - retorna o **primeiro** quando há mais de um `default: true`;
  - gera `ConfigError` quando nenhum modelo é default;
  - gera `ConfigError` quando `models` está vazio ou ausente.
- [x] Testes de integração (`../../tests/integration/config/test_config_integration.py`):
  - carregar `dev` e `prod` dos arquivos reais e verificar o modelo default resolvido.
- [ ] Testes E2E (não aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `../../app/infrastructure/config/models.py`
- `../../app/infrastructure/config/loader.py` (apenas leitura — padrão de `ConfigError`)
- `../../env.json`
- `../../env.example.json`
- `../../tests/unit/config/test_loader.py`
- `../../tests/integration/config/test_config_integration.py`
