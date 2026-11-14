# Tarefa 1.0: Modelo de domínio `ChatAnswer` (resposta em array)

<critical>Ler os arquivos `../../meus_prompts/array_response_e_streaming_response.md` (raiz), `tasks/streaming-response/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje a resposta da LLM é uma `str` única. Esta tarefa cria no domínio o modelo tipado que
representa a nova resposta em array (`{"respostas": [...]}`), com as operações que as próximas
tarefas vão usar:

- converter um JSON em `ChatAnswer`;
- converter um `ChatAnswer` em JSON;
- mesclar várias respostas sem itens duplicados;
- unir os itens em texto.

A política de cache também passa a aceitar o novo modelo.

Esta tarefa **não** muda o fluxo de busca. Ela só entrega o modelo e a política, já testados.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (o domínio não importa infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, Pydantic, métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md` (JSON inválido gera uma exceção de domínio clara, sem falha silenciosa)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Criar o modelo Pydantic `ChatAnswer` no domínio, por exemplo em `app/domain/conversation.py`
  ou em um novo `app/domain/answer.py`, e exportar em `app/domain/__init__.py`:
  - campo `respostas: list[str]` (padrão: lista vazia);
  - ao construir o modelo, descartar itens vazios ou só com espaços, removendo os espaços das pontas;
  - `from_json(raw: str) -> ChatAnswer`: converte o JSON. Se o JSON for inválido ou não tiver o
    formato esperado, lança uma exceção de domínio, por exemplo `InvalidChatAnswerError` em
    `app/domain/exceptions.py`;
  - `to_json() -> str`: serializa no formato `{"respostas": [...]}` com `ensure_ascii=False`;
  - `is_empty() -> bool`: indica se não há itens;
  - `merge(answers: list[ChatAnswer]) -> ChatAnswer`: concatena os itens na ordem recebida, sem
    duplicados (mantém a primeira ocorrência);
  - `as_text(separator: str = "\n\n") -> str`: une os itens em um texto, usado no histórico.
- Atualizar `is_cacheable_answer` (`app/application/cache/answer_policy.py`) para receber
  `ChatAnswer` e retornar `False` quando ele estiver vazio.
  - Essa função tem consumidores: o `SearchService` e o `SemanticCacheService`.
  - Para não quebrar a aplicação entre as tarefas, aceite `str | ChatAnswer` nesta tarefa. A
    tarefa 3.0 remove o suporte a `str`.
- O domínio não pode importar nada de `app/infrastructure`: o teste
  `tests/unit/domain/test_no_infrastructure_imports.py` precisa continuar passando.
</requirements>

## Subtarefas

- [x] 1.1 Criar a exceção de domínio para JSON de resposta inválido.
- [x] 1.2 Criar o modelo `ChatAnswer` com `from_json`, `to_json`, `is_empty`, `merge` e `as_text`.
- [x] 1.3 Exportar o modelo e a exceção em `app/domain/__init__.py`.
- [x] 1.4 Ajustar `is_cacheable_answer` para aceitar `ChatAnswer`.
- [x] 1.5 Criar os testes unitários do modelo e da política de cache.
- [x] 1.6 Criar o teste de integração de serialização.
- [x] 1.7 Rodar os testes, o lint e o type checking.

## Detalhes de Implementação

As regras de negócio completas estão em `tasks/streaming-response/tasks.md`, na seção
"Regras de negócio decididas", nos itens "Formato da resposta da LLM", "Vários matches semânticos"
e "Política de cache". Use o `json` da biblioteca padrão ou `model_validate_json` do Pydantic. Não
adicione dependências.

## Critérios de Sucesso

- `ChatAnswer.from_json('{"respostas": ["a", "b"]}').respostas == ["a", "b"]`.
- `ChatAnswer.from_json('{"respostas": []}').is_empty()` é `True`.
- Um JSON inválido, ou um JSON sem a chave `respostas`, lança a exceção de domínio.
- `merge` mantém a ordem e remove duplicados.
- `to_json` seguido de `from_json` devolve um objeto igual ao original.
- `is_cacheable_answer(ChatAnswer(respostas=[]))` é `False`.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade:
  - `tests/unit/domain/`: conversão válida, inválida, vazia e com itens em branco; serialização;
    `merge` com duplicados e com listas vazias; `as_text`;
  - `tests/unit/cache/`: `is_cacheable_answer` com um `ChatAnswer` vazio e com um preenchido.
- [x] Testes de integração: `tests/integration/domain/test_schema_serialization.py`, com a ida e
  volta JSON → `ChatAnswer` → JSON, incluindo acentos.
- [ ] Testes E2E: não se aplica.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/__init__.py`
- `app/domain/conversation.py` (ou o novo `app/domain/answer.py`)
- `app/domain/exceptions.py`
- `app/application/cache/answer_policy.py`
- `tests/unit/domain/`
- `tests/unit/cache/`
- `tests/integration/domain/test_schema_serialization.py`
