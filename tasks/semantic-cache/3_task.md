# Tarefa 3.0: Embedding gerado uma única vez por requisição

<critical>Ler os arquivos `../../.mine/cache_semantico.md` (raiz), `tasks/semantic-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje `SearchService._find_matches` gera o embedding da pergunta original dentro da busca no
Pinecone. Para que o mesmo vetor seja reaproveitado no cache semântico (tarefa 4.0), o
`SearchService` passa a gerar o embedding **uma única vez**, a partir da pergunta **normalizada**,
logo após o miss do cache exato, e `_find_matches` passa a recebê-lo pronto.

Esta tarefa ainda **não** usa o cache semântico; ela só prepara o fluxo. Não depende das
tarefas 1.0 e 2.0 e pode ser feita em paralelo a elas.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (orquestração na camada de aplicação)
- `.claude/code_patterns/python-conventions.md` (async, tipagem, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha de embedding mantém `OpenIaException`)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Reaproveitar `OpenAIService.generate_embedding_for_question` (não criar nova função de
  embedding; ela já usa o modelo default e aplica o `QUERY_PREFIX`).
- O texto passado ao embedding é o `normalized_text` do fingerprint já construído em
  `search()` (`build_fingerprint`), sem normalizar de novo e sem alterar `fingerprint.py`.
- `_find_matches` passa a receber `embedding: list[float]` e só consulta o Pinecone.
- O embedding **não** é gerado quando há hit no cache exato.
- `_run_pipeline` recebe o embedding pronto (a pergunta original continua indo para o
  `PayloadQuestionOpenIA` e para o histórico — só o embedding usa o texto normalizado).
- Falha ao gerar embedding: comportamento atual (`OpenIaException` propagada).
- Atualizar a docstring do módulo `app/application/search/service.py` com o novo passo.
- Manter `search()` abaixo de 30 linhas (extrair helpers se necessário).
</requirements>

## Subtarefas

- [x] 3.1 Guardar o fingerprint em `search()` e gerar o embedding do `normalized_text` após o miss exato.
- [x] 3.2 Alterar `_run_pipeline` e `_find_matches` para receberem o embedding.
- [x] 3.3 Atualizar a docstring do módulo.
- [x] 3.4 Ajustar os testes existentes do `SearchService` que assumiam o embedding da pergunta original.
- [x] 3.5 Testes de unidade novos.
- [x] 3.6 Testes de integração da API de busca.

## Detalhes de Implementação

- Motivação e mudança de comportamento: `../../.mine/cache_semantico.md`, seção 3 ("Reaproveitamento do embedding").
- Fluxo geral da busca: `tasks/techspec.md`, itens 2.2/2.3 e 3.3/3.4.
- Arquivo principal: `app/application/search/service.py`.

## Critérios de Sucesso

- Em miss exato, `generate_embedding_for_question` é chamada exatamente **uma vez**, com o texto normalizado.
- Em hit exato, não é chamada.
- O Pinecone recebe exatamente o vetor gerado.
- Todos os testes existentes continuam passando (ajustados apenas onde o comportamento mudou de propósito).

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/search/test_search_service.py`):
  - Miss exato: embedding gerado uma vez com `"onde voce vende marmitas"` para a entrada
    `"  Onde VOCÊ vende   marmitas "` (exemplo com maiúsculas, acento e espaços extras).
  - O vetor retornado pelo OpenAI é o mesmo passado a `vector_repository.query`.
  - Hit exato: `generate_embedding_for_question` não é chamada.
  - `OpenIaException` no embedding é propagada.
  - O payload da LLM e o histórico continuam usando a pergunta original.
- [x] Testes de integração (`tests/integration/api/test_search_api.py`):
  - Requisição pelos endpoints de chat/WhatsApp com OpenAI e Pinecone mockados confirma o
    embedding único com o texto normalizado.
- [x] Testes E2E: ajustar `tests/integration/api/test_e2e_flows.py` se ele verificar o texto do embedding.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/service.py`
- `app/application/cache/fingerprint.py` (apenas leitura — não alterar)
- `app/infrastructure/openai/service.py` (apenas leitura)
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
