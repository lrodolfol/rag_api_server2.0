# Tarefa 2.0: OpenAI com saída JSON forçada retornando `ChatAnswer`

<critical>Ler os arquivos `../../meus_prompts/array_response_e_streaming_response.md` (raiz), `tasks/streaming-response/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Esta tarefa faz a OpenAI **sempre** responder no formato `{"respostas": [...]}`, usando o modo JSON
da Responses API e um prompt ajustado. Com isso, `OpenAIService.generate_chat_answer` passa a
retornar um `ChatAnswer` em vez de uma `str`.

O contrato de `generate_chat_answer` e o seu consumidor, o `SearchService`, mudam **juntos** nesta
tarefa, para a aplicação não ficar quebrada entre uma tarefa e outra. Por isso, o `SearchService`
recebe aqui uma **adaptação mínima**: converte o `ChatAnswer` com `as_text()` para manter o fluxo
atual em string. A adaptação completa fica para a tarefa 3.0.

Depende da tarefa 1.0 (`ChatAnswer` e a exceção de domínio).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (a conversão do JSON acontece na fronteira da infraestrutura e o domínio fica tipado)
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md` (JSON inválido: `logger.error` e "não encontrado", sem falha silenciosa)
- `.claude/code_patterns/security.md` (nunca logar a resposta da LLM)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `app/infrastructure/openai/service.py`:
  - a chamada de chat (`_create_response`) usa o formato de texto JSON da Responses API
    (`text={"format": {"type": "json_object"}}`). A chamada de moderação **não** muda;
  - `generate_chat_answer(...) -> ChatAnswer`:
    - payload inválido (`payload.is_invalid()`): retorna `ChatAnswer(respostas=[])`;
    - resposta vazia: retorna `ChatAnswer(respostas=[])`;
    - JSON inválido (a exceção de domínio da tarefa 1.0): `logger.error`, sem o conteúdo, e retorna
      `ChatAnswer(respostas=[])`;
    - reaproveitar `_strip_code_fence` antes da conversão, porque a LLM pode envolver o JSON em
      um bloco de código markdown;
  - logar a quantidade de itens recebidos;
  - manter os métodos com menos de 30 linhas.
- `app/domain/prompts.py` (`INPUT_GUIDE`):
  - exigir que **toda** resposta seja um JSON `{"respostas": [...]}`, inclusive cumprimentos
    (um item) e "não encontrado" (`{"respostas": []}`);
  - o modo `json_object` da OpenAI exige a palavra "JSON" no prompt; confira que ela está lá;
  - o prompt já foi parcialmente editado (diff local não commitado). Ajuste a partir dele, sem
    reverter as outras mudanças do autor.
- `env.json` e `env.example.json`: `fingerprint.prompt_version` de `1.0.0` para `2.0.0`, nas duas
  ocorrências de cada arquivo, para invalidar o cache antigo em texto puro.
- `app/application/search/service.py`: adaptação mínima em `_run_pipeline`, que converte o retorno
  com `.as_text()` para manter a assinatura atual em `str`. A tarefa 3.0 substitui isso.
</requirements>

## Subtarefas

- [x] 2.1 Ativar o formato JSON na chamada de chat da OpenAI.
- [x] 2.2 Fazer `generate_chat_answer` converter a resposta e retornar `ChatAnswer`, incluindo o caminho de JSON inválido.
- [x] 2.3 Ajustar o `INPUT_GUIDE` para exigir o JSON em todas as respostas.
- [x] 2.4 Incrementar `prompt_version` em `env.json` e `env.example.json`.
- [x] 2.5 Adaptar `_run_pipeline` do `SearchService` (`.as_text()`).
- [x] 2.6 Atualizar os testes unitários e de integração da OpenAI e do `SearchService` afetados.
- [x] 2.7 Rodar os testes, o lint e o type checking.

## Detalhes de Implementação

As regras estão em `tasks/streaming-response/tasks.md`, nos itens "JSON forçado na OpenAI",
"JSON inválido mesmo com o modo forçado" e "Invalidação do cache antigo". Veja o fluxo da LLM na
seção 2 de `tasks/techspec.md`.

## Critérios de Sucesso

- A chamada de chat da OpenAI é feita com o formato `json_object`, conferido no mock do cliente.
- Com uma resposta JSON válida, o retorno é um `ChatAnswer` com os itens corretos.
- Com um JSON envolto em bloco de código, a conversão funciona.
- Com um JSON inválido ou uma resposta vazia, o retorno é um `ChatAnswer` vazio e um erro é logado
  sem o conteúdo.
- A moderação continua funcionando como antes.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/openai/test_service.py`):
  - formato `json_object` enviado na chamada de chat;
  - JSON válido, JSON em bloco de código, JSON inválido, resposta vazia e payload inválido;
  - nenhum log com o conteúdo da resposta (`caplog`).
- [x] Testes de unidade (`tests/unit/search/test_search_service.py`): ajustar os mocks de
  `generate_chat_answer` para retornar `ChatAnswer`.
- [x] Testes de integração (`tests/integration/openai/test_openai_integration.py`): atualizar os
  fakes do cliente para devolver JSON e validar o `ChatAnswer` retornado.
- [x] Testes E2E: rodar `tests/integration/api/` e ajustar os fakes de OpenAI que devolvem texto puro.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/openai/service.py`
- `app/domain/prompts.py`
- `app/application/search/service.py` (adaptação mínima)
- `env.json` e `env.example.json`
- `tests/unit/openai/test_service.py`
- `tests/unit/search/test_search_service.py`
- `tests/integration/openai/test_openai_integration.py`
- `tests/integration/api/test_search_api.py` e `tests/integration/api/test_e2e_flows.py` (fakes)
