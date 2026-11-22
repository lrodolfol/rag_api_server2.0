# Tarefa 2.0: `SearchService` grava os matches do RAG no histórico

<critical>Ler os arquivos `../../meus_prompts/client_histotic_refactor.md` (raiz), `tasks/client-history-matches/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Leva os matches da busca vetorial, obtidos em `_run_pipeline`, até `_persist_turn`, que passa a
gravar a mensagem do assistente com `context.rag_matches`. Respostas vindas do cache exato ou do
cache semântico continuam sendo gravadas sem `context`.

Depende da tarefa 1.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (orquestração na camada de aplicação)
- `.claude/code_patterns/python-conventions.md` (tipagem, `NamedTuple`, métodos < 30 linhas, clean code)
- `.claude/code_patterns/security.md` (não logar o conteúdo dos matches)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Em `app/application/search/service.py`:
  - `_PipelineResult` passa a carregar também os textos dos matches (ex.: `rag_matches: list[str]`),
    reaproveitando `_to_phrases(matches)` — não duplicar a extração.
  - O valor precisa chegar até `search()` → `_persist_turn`. Hoje `_answer_on_cache_miss`
    retorna só `ChatAnswer`; ajustar o retorno (ex.: um `NamedTuple` com a resposta e os
    matches) mantendo os métodos pequenos (< 30 linhas) e tipados.
  - Cache exato e cache semântico: nenhum match → `context` `None`.
  - `_persist_turn` recebe os matches e, quando houver, monta
    `MessageHistoryItem(role=ASSISTANT, text=answer.as_text(), context=MessageContext(rag_matches=...))`.
    Sem matches (lista vazia), grava sem `context`.
  - Mensagem do usuário inalterada. Resposta vazia continua sem mensagem do assistente.
- Não gravar o contexto nos caches exato/semântico (`_store_answer` inalterado).
- Não alterar `OpenAIService`.
- Atualizar a docstring do módulo (item "persist the question/answer turn").
</requirements>

## Subtarefas

- [x] 2.1 Incluir os textos dos matches em `_PipelineResult`.
- [x] 2.2 Propagar os matches de `_answer_on_cache_miss` até `search()`.
- [x] 2.3 Alterar `_persist_turn` para gravar `context.rag_matches` quando houver matches.
- [x] 2.4 Atualizar os testes unitários existentes do `SearchService` e criar os novos.
- [x] 2.5 Atualizar os testes de integração da API de busca.
- [x] 2.6 Rodar testes, lint e type checking do projeto.

## Detalhes de Implementação

Regras completas na seção "Regras de negócio decididas" de `tasks/client-history-matches/tasks.md`.
O texto de cada match vem de `VectorMatch.text` (`app/infrastructure/pinecone/models.py`), o mesmo
valor já enviado ao LLM via `_to_phrases`.

## Critérios de Sucesso

- Fluxo RAG completo: a mensagem do assistente gravada tem `context.rag_matches` igual aos textos
  dos matches, na ordem do Pinecone.
- Fluxo RAG sem matches: a mensagem do assistente (se houver) é gravada sem `context`.
- Hit no cache exato ou semântico: a mensagem do assistente é gravada sem `context`.
- Resposta vazia: só a mensagem do usuário é gravada (comportamento atual).
- Caches exato e semântico continuam gravando exatamente o mesmo conteúdo de hoje.
- Nenhum log contém o texto dos matches.
- Nenhum teste existente quebra (exceto os que precisam refletir o novo comportamento); lint e
  type checking sem erros.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/search/test_search_service.py`):
  - revisar `test_should_persist_question_and_joined_items_on_given_channel` para validar o
    `context.rag_matches`;
  - novo: pipeline sem matches → assistente sem `context`;
  - revisar `test_should_persist_turn_in_history_on_cache_hit` → assistente sem `context`;
  - revisar `test_should_store_semantic_answer_json_in_exact_cache_and_text_in_history` →
    assistente sem `context`;
  - `test_should_not_persist_assistant_turn_when_answer_is_empty` continua passando;
  - novo: os valores gravados nos caches exato/semântico não incluem os matches.
- [x] Testes de integração (`tests/integration/api/test_search_api.py` e
  `tests/integration/api/test_e2e_flows.py`): após uma busca pelo pipeline, o histórico no Redis
  contém a mensagem do assistente com `context.rag_matches`; após um hit de cache, sem `context`.
- [x] Testes E2E: cobertos pelos fluxos de `test_e2e_flows.py`.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/domain/conversation.py` (modelo da tarefa 1.0 — somente leitura)
- `app/infrastructure/pinecone/models.py` (`VectorMatch` — somente leitura)
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
