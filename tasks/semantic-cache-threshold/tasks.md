# Resumo de Tarefas de Implementação do Threshold no Cache Semântico

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../.mine/semantic_cache_threshold.md` (raiz do repositório).
**Cache semântico existente:** `../../.mine/cache_semantico.md` (raiz) e `tasks/semantic-cache/tasks.md`
(regras de negócio do fluxo atual).
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- **Threshold:** constante `SIMILARITY_THRESHOLD = 0.91` na classe `SearchService`
  (`app/application/search/service.py`), valor fixo conforme o documento de requisitos.
- **Comparação:** um resultado é aceito quando `similarity >= SIMILARITY_THRESHOLD`
  (o valor exato 0.91 é aceito). Resultados abaixo são ignorados.
- **Vários resultados aceitos:** as respostas são **deduplicadas** (texto idêntico aparece uma
  única vez), mantendo a ordem do repositório (mais similar primeiro), e concatenadas em uma
  única string separadas por **quebra dupla de linha** (`"\n\n"`).
  A introdução aleatória é aplicada depois, sobre a string já concatenada (ver
  `../cache/tasks.md`, "Mensagens aleatórias na resposta ao usuário").
- **Nenhum resultado aceito** (ou lista vazia) = **miss semântico**: segue o fluxo normal de
  RAG + LLM, exatamente como hoje.
- **Hit semântico** (pelo menos um resultado aceito): mantém o comportamento atual — retorna a
  string concatenada sem RAG/LLM, grava no Redis com a chave do fingerprint atual e grava o
  turno no histórico.
- **`SemanticCacheService.find_answer`** passa a retornar `list[SemanticCacheMatch]` (todos os
  resultados da consulta, `[]` em miss). Retorna os matches e não strings porque o threshold
  depende do campo `similarity`.
- **`PostgresSemanticCacheRepository.find_nearest` NÃO é alterado.** A quantidade de
  resultados continua limitada por `semantic_cache.top_k`.
- **Logs:** mantêm a regra atual — hit/miss com no máximo 8 caracteres da chave; nunca
  pergunta, resposta ou embedding. Pode-se logar a quantidade de resultados aceitos.

## Fora de escopo

- Tornar o threshold configurável via `env.json` (o documento pede valor fixo).
- Alterações no SQL, no repositório PostgreSQL ou na gravação do cache semântico.

## Tarefas

- [x] 1.0 Avaliação por threshold no `SearchService`
- [x] 2.0 `find_answer` retorna todos os resultados e o fluxo de busca usa o threshold
