# Tarefa 2.0: `find_answer` retorna todos os resultados e o fluxo de busca usa o threshold

<critical>Ler os arquivos `../../.mine/semantic_cache_threshold.md` (raiz), `tasks/semantic-cache-threshold/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Hoje `SemanticCacheService.find_answer` devolve sempre a resposta do primeiro resultado,
mesmo com similaridade baixa. Esta tarefa faz `find_answer` devolver **todos** os resultados
da consulta e faz `_answer_from_semantic_cache` usar o `threshold_evaluate` criado na
tarefa 1.0 para decidir entre hit e miss.

O contrato de `find_answer` e o seu consumidor mudam **juntos** nesta tarefa, para a aplicação
não ficar quebrada entre uma tarefa e outra.

Depende da tarefa 1.0 (`SIMILARITY_THRESHOLD` e `threshold_evaluate`).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviço de aplicação não conhece SQL; repositório intocado)
- `.claude/code_patterns/python-conventions.md` (tipagem, métodos < 30 linhas)
- `.claude/code_patterns/error-handling.md` (falha do PostgreSQL continua sendo miss)
- `.claude/code_patterns/security.md` (logs sem pergunta/resposta/embedding)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `SemanticCacheService.find_answer` (`app/application/cache/semantic_cache_service.py`):
  - nova assinatura: `async find_answer(fingerprint, embedding) -> list[SemanticCacheMatch]`;
  - retorna a lista completa recebida de `find_nearest` (`[]` em miss/falha);
  - remove o uso de `best_match` / `matches[0]`;
  - atualizar a docstring do módulo, que hoje diz "no minimum similarity threshold is applied".
- `SearchService._answer_from_semantic_cache` (`app/application/search/service.py`):
  - a variável `answer` passa a receber a lista retornada por `find_answer`;
  - chama `threshold_evaluate` com essa lista;
  - resultado `None` → log de miss e retorna `None` (fluxo segue para o RAG);
  - resultado string → log de hit, grava no Redis (`self._answer_cache.set`) e retorna a string;
  - manter o método com menos de 30 linhas.
- **NÃO alterar** `PostgresSemanticCacheRepository.find_nearest`
  (`app/infrastructure/postgres/semantic_cache_repository.py`).
- Atualizar a docstring do módulo `search/service.py` (item do fluxo sobre o cache semântico)
  para mencionar o threshold.
</requirements>

## Subtarefas

- [x] 2.1 Refatorar `find_answer` para retornar `list[SemanticCacheMatch]`.
- [x] 2.2 Refatorar `_answer_from_semantic_cache` para receber a lista e usar `threshold_evaluate`.
- [x] 2.3 Refatorar os testes unitários de `SemanticCacheService`.
- [x] 2.4 Refatorar os testes unitários do `SearchService` que mockam `find_answer`.
- [x] 2.5 Ajustar/adicionar testes de integração do fluxo com threshold.
- [x] 2.6 Rodar testes, lint e type checking do projeto.

## Detalhes de Implementação

Regras completas na seção "Regras de negócio decididas" de `tasks/semantic-cache-threshold/tasks.md`.
O comportamento de hit (Redis + histórico, sem RAG/LLM) e de miss (RAG + gravação nos dois
caches) é o mesmo descrito em `tasks/semantic-cache/tasks.md`. Só muda **o critério** de hit.

Pontos de atenção nos testes:

- `tests/unit/search/test_search_service.py`: o helper de mocks configura
  `self.semantic_cache.find_answer.return_value = semantic_answer` (string). Passa a ser uma
  lista de `SemanticCacheMatch`; o caso de miss usa `[]`.
- `tests/unit/cache/test_semantic_cache_service.py`: os testes
  `test_should_return_answer_of_best_match`, `test_should_return_none_when_no_match` e
  `test_should_return_best_match_regardless_of_similarity` descrevem o comportamento antigo e
  devem ser reescritos para o novo contrato (eles estão incorretos para a nova regra).
- Testes de integração (`tests/integration/api/test_search_api.py` e
  `tests/integration/api/test_e2e_flows.py`) usam o fake de PostgreSQL da fixture
  `semantic_cache_db` (`tests/integration/conftest.py`), que calcula `similarity = 1 - distância
  de cosseno` de verdade. Os cenários atuais usam o mesmo embedding (similaridade 1.0) e devem
  continuar passando; acrescente um cenário com embedding pouco similar para validar o miss.

## Critérios de Sucesso

- `find_answer` retorna todos os matches do repositório, na mesma ordem.
- Com todos os matches abaixo de 0.91, a busca roda RAG + LLM e grava nos dois caches (miss).
- Com pelo menos um match >= 0.91, a resposta vem do cache semântico (string concatenada),
  sem RAG/LLM, e é gravada no Redis e no histórico (hit).
- Falha do PostgreSQL continua sendo tratada como miss.
- `find_nearest` sem nenhuma alteração no diff.
- Toda a suíte de testes passa; lint e type checking sem erros.

## Testes da Tarefa

- [x] Testes de unidade:
  - `SemanticCacheService.find_answer`: retorna a lista completa; retorna `[]` quando o
    repositório não encontra nada; não filtra por similaridade (o filtro é do `SearchService`).
  - `SearchService`: hit quando há match >= 0.91 (sem RAG/LLM, grava no Redis e no histórico);
    miss quando todos < 0.91 (roda RAG/LLM e grava nos dois caches); miss com lista vazia;
    hit com vários matches retorna as respostas concatenadas com `"\n\n"`.
- [x] Testes de integração (`test_search_api.py`, para `/whatsapp` e `/chat`):
  - pergunta similar (similaridade >= 0.91) continua respondida pelo cache semântico;
  - pergunta com embedding pouco similar (< 0.91) roda o RAG e grava uma nova linha no cache semântico.
- [x] Testes E2E: rodar `tests/integration/api/test_e2e_flows.py` e ajustar se algum fluxo
  depender do comportamento antigo.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/cache/semantic_cache_service.py`
- `app/application/search/service.py`
- `app/infrastructure/postgres/semantic_cache_repository.py` (somente leitura — não alterar)
- `tests/unit/cache/test_semantic_cache_service.py`
- `tests/unit/search/test_search_service.py`
- `tests/integration/api/test_search_api.py`
- `tests/integration/api/test_e2e_flows.py`
- `tests/integration/conftest.py` (fixture `semantic_cache_db` — somente leitura)
