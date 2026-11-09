# Tarefa 2.0: Moderação com classificação da categoria (`OpenAIService.moderate`)

<critical>Ler os arquivos `divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje a moderação só diz se o conteúdo do cliente tem ofensas. Esta tarefa faz a mesma chamada à
LLM também classificar o serviço em uma das categorias informadas, ou sugerir uma nova quando
nenhuma servir.

Esta tarefa **não** consulta o Redis e não muda o `RegistrationService`. Quem chamar `moderate`
passa a lista de categorias (a integração é a tarefa 5.0).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md`
- `.claude/code_patterns/python-conventions.md`
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/security.md` (não registrar o conteúdo do cliente nem a resposta bruta da LLM)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Mudar a assinatura para `async moderate(content: str, categories: list[str]) -> ModerationResult`.
- Atualizar `_MODERATION_PROMPT` em `app/infrastructure/openai/service.py`:
  - informar a lista de categorias (uma por linha);
  - pedir que a LLM escolha **exatamente uma** categoria da lista, escrita como está na lista;
  - se nenhuma servir, pedir que ela sugira **uma** categoria nova, curta, em português e em
    maiúsculas;
  - pedir o JSON no formato `{"insult": true/false, "insult_text": "...", "categoria": "..."}`.
- Com a lista de categorias vazia, o prompt continua válido e pede só a sugestão de uma categoria.
- Adicionar `category: str = Field(default="")` ao `ModerationResult`
  (`app/infrastructure/openai/models.py`) e preenchê-lo em `_parse_moderation` a partir da chave
  `categoria`, sem espaços nas pontas. Uma chave ausente resulta em `""`. O `fallback` é aplicado
  depois, no serviço de categorias.
- O tratamento atual de JSON inválido (`OpenIaException`) não muda.
- Atualizar todas as chamadas existentes de `moderate` para compilar. Até a tarefa 5.0, o
  `RegistrationService` pode passar `[]`.
- Registrar em log a categoria devolvida pela LLM (só o nome da categoria).
</requirements>

## Subtarefas

- [x] 2.1 Adicionar `category` ao `ModerationResult`.
- [x] 2.2 Atualizar o prompt de moderação e a assinatura de `moderate`.
- [x] 2.3 Ler o campo `categoria` em `_parse_moderation`.
- [x] 2.4 Ajustar as chamadas existentes de `moderate`.
- [x] 2.5 Criar ou atualizar os testes unitários e de integração.
- [x] 2.6 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

O formato da resposta e a regra da categoria nova estão em `tasks/divisao-categorias/tasks.md`,
na seção "Cadastro". O prompt continua sendo uma constante `Final` do módulo, formatada com
`str.format`. Lembre-se de escapar as chaves do JSON (`{{` e `}}`), como o prompt atual já faz.

## Critérios de Sucesso

- O prompt enviado à OpenAI contém todas as categorias recebidas.
- Uma resposta `{"insult": false, "insult_text": "", "categoria": "ALIMENTAÇÃO"}` vira
  `ModerationResult(insult=False, insult_text="", category="ALIMENTAÇÃO")`.
- Uma resposta sem `categoria` vira `category=""`, sem erro.
- Um JSON inválido continua lançando `OpenIaException`.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/openai/test_service.py`): o prompt inclui as categorias,
  com e sem lista vazia; parse com `categoria`, sem `categoria` e com espaços; JSON inválido;
  resposta dentro de bloco de código (```` ```json ````).
- [x] Testes de integração (`tests/integration/openai/test_openai_integration.py`): seguir o
  padrão existente e validar que `moderate` com uma lista de categorias devolve um
  `ModerationResult` com `category` preenchido.
- [x] Testes E2E: não se aplica.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/openai/service.py`
- `app/infrastructure/openai/models.py`
- `app/application/registration/service.py` (só o ajuste da chamada)
- `tests/unit/openai/test_service.py`
- `tests/integration/openai/test_openai_integration.py`
