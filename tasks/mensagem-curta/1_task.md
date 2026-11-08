# Tarefa 1.0: Detector de mensagem curta (`is_short_message`)

<critical>Ler os arquivos `identificar_mensagem_curta.md` (raiz), `tasks/mensagem-curta/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje toda mensagem recebida segue para o fluxo RAG completo, inclusive mensagens como `"..."` ou
`"1234"`, que não têm conteúdo útil. Esta tarefa cria uma função pura e tipada que diz se uma
mensagem é curta, **sem chamar LLM**.

Esta tarefa **não** muda o fluxo de busca. Ela só entrega a função, já testada. A tarefa 2.0 faz a
integração.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (regra de texto sem dependência de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem, constantes `Final`, funções com menos de 30 linhas)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Criar a função `is_short_message(message: str) -> bool` em
  `app/application/text_processing/`, junto de `normalize_text`. Pode ficar em
  `text_processor.py` ou em um novo módulo, por exemplo `message_validator.py`.
- Seguir a regra de "mensagem curta" descrita em `tasks/mensagem-curta/tasks.md`, na seção
  "Regras de negócio decididas":
  - retorna `True` quando a mensagem tem menos de 2 letras;
  - só contam caracteres alfabéticos Unicode, como os de `str.isalpha()`, incluindo os acentuados.
- O mínimo de letras deve ser uma constante do módulo, por exemplo
  `MIN_MESSAGE_LETTERS: Final[int] = 2`. Não use um número solto no código.
- Usar apenas a biblioteca padrão. Não adicione dependências.
- Exportar a função (e a constante) em `app/application/text_processing/__init__.py`, atualizando
  `__all__` e a docstring do pacote.
- A função não registra logs e não lança exceções para nenhuma `str`.
</requirements>

## Subtarefas

- [x] 1.1 Criar a constante do mínimo de letras e a função `is_short_message`.
- [x] 1.2 Exportar a função e a constante em `app/application/text_processing/__init__.py`.
- [x] 1.3 Criar os testes unitários parametrizados.
- [x] 1.4 Criar o teste de integração do pacote.
- [x] 1.5 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

A regra completa e a lista de exemplos estão em `tasks/mensagem-curta/tasks.md`, nas seções
"Regras de negócio decididas" e "Fora de escopo". Uma implementação simples conta os caracteres em
que `char.isalpha()` é verdadeiro e compara o total com a constante. Não é preciso usar regex.

## Critérios de Sucesso

- `is_short_message` retorna `True` para todos os exemplos do documento original: `"..."`, `"i"`,
  `"!!"`, `"1234"`, `" "` e `"   "`.
- Também retorna `True` para `""`, `"a1"`, `"é?"` e `"😀😀"`.
- Retorna `False` para `"oi"`, `"ok"`, `"  oi  "`, `"pizzaria no centro"` e `"onde tem açaí?"`.
- Nenhuma dependência nova foi adicionada.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade: em `tests/unit/text_processing/` (no `test_text_processor.py` existente
  ou em um novo `test_message_validator.py`), um teste parametrizado com os casos curtos (`True`) e
  outro com os casos válidos (`False`), incluindo acentos, números, pontuação, emojis e espaços nas
  pontas.
- [x] Testes de integração: em `tests/integration/text_processing/`, importar
  `is_short_message` pelo pacote `app.application.text_processing` e validar um caso curto e um
  válido. Assim, a exportação pública fica garantida.
- [ ] Testes E2E: não se aplica. O fluxo HTTP é coberto na tarefa 2.0.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/text_processing/__init__.py`
- `app/application/text_processing/text_processor.py` (ou o novo `message_validator.py`)
- `tests/unit/text_processing/`
- `tests/integration/text_processing/`
