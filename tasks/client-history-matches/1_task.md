# Tarefa 1.0: Modelo de domínio com `context` opcional e serialização no Redis

<critical>Ler os arquivos `../../meus_prompts/client_histotic_refactor.md` (raiz), `tasks/client-history-matches/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Prepara o modelo do histórico para guardar os matches do RAG: adiciona à mensagem do histórico
um campo opcional `context` com a lista `rag_matches`, e ajusta o repositório Redis para não
gravar `context` quando ele é `None`.

Esta tarefa **apenas adiciona** capacidade: o `SearchService` ainda não preenche o campo (isso
é a tarefa 2.0). Ao final, a aplicação continua funcionando como hoje e o JSON gravado é idêntico
ao atual.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (modelo na camada de domínio, serialização na infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, modelos Pydantic, clean code)
- `.claude/code_patterns/security.md` (não logar conteúdo dos matches)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Em `app/domain/conversation.py`, criar um modelo Pydantic para o contexto (ex.:
  `MessageContext`) com o campo `rag_matches: list[str]` (default lista vazia).
- Adicionar em `MessageHistoryItem` o campo `context: MessageContext | None = None`.
- Exportar o novo modelo em `app/domain/__init__.py`, seguindo o padrão existente.
- Em `RedisHistoryRepository._serialize` (`app/infrastructure/redis/repository.py`), gravar sem
  campos `None` (ex.: `model_dump_json(exclude_none=True)`), para que mensagens sem contexto
  fiquem exatamente como hoje: `{"role": "...", "text": "..."}`.
- `_deserialize` deve continuar aceitando itens antigos sem `context` e passar a aceitar itens
  com `context`.
- Não alterar `OpenAIService._build_history`: o LLM continua recebendo só `role` e `text`.
- Atualizar docstrings dos modelos/repositório que descrevem o formato gravado.
</requirements>

## Subtarefas

- [x] 1.1 Criar o modelo de contexto e o campo opcional `context` em `MessageHistoryItem`.
- [x] 1.2 Exportar o novo modelo em `app/domain/__init__.py`.
- [x] 1.3 Ajustar `_serialize` para omitir campos `None`.
- [x] 1.4 Criar/atualizar testes unitários e de integração.
- [x] 1.5 Rodar testes, lint e type checking do projeto.

## Detalhes de Implementação

Formato e regras na seção "Regras de negócio decididas" de `tasks/client-history-matches/tasks.md`.
Arquitetura de camadas e convenções em `tasks/techspec.md` e `.claude/code_patterns/`.

## Critérios de Sucesso

- `MessageHistoryItem(role=..., text=...)` continua válido e `context` é `None` por padrão.
- Mensagem sem `context` é gravada no Redis sem a chave `context`.
- Mensagem com `context` é gravada e lida de volta com os mesmos `rag_matches`, na mesma ordem.
- Itens antigos (sem `context`) são lidos sem erro.
- Nenhum teste existente quebra; lint e type checking sem erros.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/domain/test_conversation.py`: `context` default `None`; criação com
    `rag_matches`; `rag_matches` default lista vazia.
  - `tests/unit/redis/test_history_repository.py`: grava/lê mensagem com `context`
    (round-trip); mensagem sem `context` não contém a chave no JSON salvo; leitura de item
    antigo sem `context`.
- [x] Testes de integração (`tests/integration/redis/test_history_integration.py`): round-trip
  de uma mensagem do assistente com `context` no Redis.
- [ ] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/conversation.py`
- `app/domain/__init__.py`
- `app/infrastructure/redis/repository.py`
- `tests/unit/domain/test_conversation.py`
- `tests/unit/redis/test_history_repository.py`
- `tests/integration/redis/test_history_integration.py`
