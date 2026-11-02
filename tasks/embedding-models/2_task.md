# Tarefa 2.0: `OpenAIService` passa a usar o modelo default resolvido

<critical>Ler os arquivos `../../.mine/refatoracao_modelo_embedding.md` (raiz), `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

O `OpenAIService` gera embeddings usando `self._config.model_embeddings`, campo que deixa de existir
na Tarefa 1.0. Esta tarefa faz o serviço usar o modelo default resolvido pela configuração e
atualiza os testes que montam `OpenAIConfig` no formato antigo.

<skills>
### Conformidade com Skills Padrões

- `../../.claude/code_patterns/architecture.md`
- `../../.claude/code_patterns/python-conventions.md` (tipagem, métodos < 30 linhas)
- `../../.claude/code_patterns/error-handling.md` (manter a tradução `OpenAIError` → `OpenIaException`)
- `../../.claude/code_patterns/testing.md`
</skills>

<requirements>
- Depende da Tarefa 1.0 (`OpenAIConfig.models` e resolução do default).
- `_generate_vector` em `app/infrastructure/openai/service.py` passa a usar o modelo default
  resolvido pela configuração (ex.: `self._config.default_model_embeddings`).
- O serviço **não** deve reimplementar a regra "primeiro com `default: true`" — apenas consumir
  o que a configuração expõe (sem duplicar lógica).
- Não alterar a assinatura pública do serviço, o tratamento de erros, nem o fluxo de chat
  (`model_chat`).
- Não alterar `app/api/dependencies.py` (a injeção continua passando `config.open_ai`).
</requirements>

## Subtarefas

- [x] 2.1 Trocar a referência ao modelo em `_generate_vector`.
- [x] 2.2 Atualizar a construção de `OpenAIConfig` em `../../tests/unit/openai/test_service.py`.
- [x] 2.3 Atualizar a construção de `OpenAIConfig` em `../../tests/integration/openai/test_openai_integration.py`.
- [x] 2.4 Adicionar testes que verificam qual modelo é enviado à OpenAI.

## Detalhes de Implementação

- Geração de embeddings no fluxo: `../techspec.md` §1.4 (cadastro) e §2.2 (mensagem do usuário).
- Regra de seleção do modelo: `tasks.md` (seção "Regras de negócio decididas").

## Critérios de Sucesso

- `embeddings.create` é chamado com `model` igual ao modelo default da configuração.
- Nenhum uso do campo antigo `OpenAIConfig.model_embeddings` permanece no código ou nos testes.
- Toda a suíte (`python -m pytest` dentro do `.venv`), lint e type checking passam.

## Testes da Tarefa

- [x] Testes de unidade (`../../tests/unit/openai/test_service.py`):
  - com dois modelos (`economic` default, `stronger` não default), o `model` enviado é o do `economic`;
  - trocando o default para `stronger`, o `model` enviado muda de acordo.
- [x] Testes de integração (`../../tests/integration/openai/test_openai_integration.py`):
  - fluxo de geração de embedding com `OpenAIConfig` no formato novo usa o modelo default.
- [ ] Testes E2E (não aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `../../app/infrastructure/openai/service.py`
- `../../tests/unit/openai/test_service.py`
- `../../tests/integration/openai/test_openai_integration.py`
