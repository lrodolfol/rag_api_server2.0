# Tarefa 1.0: Avaliação por threshold no `SearchService`

<critical>Ler os arquivos `../../.mine/semantic_cache_threshold.md` (raiz), `tasks/semantic-cache-threshold/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Adiciona ao `SearchService` a regra de threshold de similaridade: uma constante
`SIMILARITY_THRESHOLD` e o método `threshold_evaluate`, que recebe a lista de resultados do
cache semântico e devolve uma única string com as respostas aceitas (ou `None` quando nenhuma
passa no threshold).

Esta tarefa **apenas adiciona** código: o fluxo de busca ainda não chama `threshold_evaluate`
(isso é feito na tarefa 2.0). Assim a aplicação continua funcionando ao final desta tarefa.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (regra de negócio na camada de aplicação)
- `.claude/code_patterns/python-conventions.md` (tipagem, `Final`, métodos < 30 linhas, clean code)
- `.claude/code_patterns/security.md` (não logar respostas)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Constante de classe `SIMILARITY_THRESHOLD: Final[float] = 0.91` em `SearchService`
  (`app/application/search/service.py`). Valor fixo, **não** vai para `env.json`.
- Novo método `threshold_evaluate(self, matches: list[SemanticCacheMatch]) -> str | None` no
  `SearchService` (pode ser `@staticmethod`/`@classmethod` se não usar estado da instância):
  - percorre a lista e aceita apenas os matches com `similarity >= SIMILARITY_THRESHOLD`;
  - ignora os matches com `similarity < SIMILARITY_THRESHOLD`;
  - deduplica respostas com texto idêntico, mantendo a ordem original (mais similar primeiro);
  - concatena as respostas aceitas com `"\n\n"` e retorna a string;
  - retorna `None` quando nenhum match é aceito ou a lista está vazia.
- Importar `SemanticCacheMatch` de `app.domain` (já existe em `app/domain/cache.py`).
- Não alterar `_answer_from_semantic_cache`, `SemanticCacheService` nem o repositório nesta tarefa.
- Atualizar a docstring do módulo/classe se ela descrever o comportamento do cache semântico.
</requirements>

## Subtarefas

- [x] 1.1 Criar a constante `SIMILARITY_THRESHOLD` no `SearchService`.
- [x] 1.2 Implementar `threshold_evaluate` conforme os requisitos.
- [x] 1.3 Criar os testes unitários de `threshold_evaluate` em `tests/unit/search/test_search_service.py`.
- [x] 1.4 Rodar testes, lint e type checking do projeto.

## Detalhes de Implementação

Regras completas na seção "Regras de negócio decididas" de `tasks/semantic-cache-threshold/tasks.md`.
O modelo de entrada é `SemanticCacheMatch` (`input_text`, `response`, `distance`, `similarity`),
definido em `app/domain/cache.py`.

## Critérios de Sucesso

- `threshold_evaluate` retorna `None` para lista vazia e para lista com todos os matches abaixo de 0.91.
- Um match com `similarity == 0.91` é aceito.
- Com vários matches aceitos, o retorno é a junção das respostas com `"\n\n"`, na ordem recebida, sem duplicadas.
- Matches abaixo do threshold nunca aparecem no retorno, mesmo misturados com matches aceitos.
- Nenhum teste existente quebra; lint e type checking sem erros.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/search/test_search_service.py`):
  - lista vazia → `None`;
  - todos abaixo do threshold → `None`;
  - um match exatamente em 0.91 → aceito;
  - um match aceito → retorna somente a resposta dele;
  - vários aceitos → respostas unidas com `"\n\n"` na ordem recebida;
  - aceitos e rejeitados misturados → somente os aceitos;
  - respostas duplicadas entre os aceitos → aparecem uma única vez.
- [x] Testes de integração: não há mudança de fluxo nesta tarefa; rodar a suíte de integração
  existente para garantir que nada quebrou.
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/domain/cache.py` (`SemanticCacheMatch` — somente leitura)
- `tests/unit/search/test_search_service.py`
