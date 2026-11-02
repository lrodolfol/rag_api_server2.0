# Tarefa 2.0: Geração do fingerprint e da chave de cache

<critical>Ler os arquivos `../../.mine/implementacao_cahce.md` (raiz), `tasks/cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar as funções puras que transformam a pergunta do usuário e a configuração
`finger_print` (tarefa 1.0) em uma chave de cache determinística. Não há acesso ao Redis nem
mudança no fluxo de busca nesta tarefa. A saída é um módulo testável isoladamente, consumido
pelas tarefas 3.0 e 4.0.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (modelo no domínio; regra de montagem na aplicação; domínio sem imports de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (tipagem forte, modelos em vez de `dict`, funções pequenas)
- `.claude/code_patterns/security.md` (o texto da pergunta nunca vai para os logs)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Modelo de domínio `CacheFingerprint` (Pydantic, imutável — `frozen=True`) em `app/domain/cache.py`
  com `prompt_version`, `rules_version`, `model_capability` e `normalized_text`, todos `str`.
  Exportar em `app/domain/__init__.py`.
  - O domínio **não** pode importar infraestrutura (há um teste que verifica isso:
    `tests/unit/domain/test_no_infrastructure_imports.py`).
- Módulo `app/application/cache/fingerprint.py` com:
  - `normalize_question_finger_print(question: str) -> str`: `strip()`, minúsculas e colapso de qualquer sequência
    de espaços, tabs ou quebras de linha em um único espaço. Remova também os acentos.
    **Não** reutilizar `normalize_text` de `text_processing`: ela tem outra finalidade
    (remover linhas em branco para chunking).
  - `build_fingerprint(question: str, config: FingerPrintConfig) -> CacheFingerprint`.
  - `build_cache_key(fingerprint: CacheFingerprint) -> str`: SHA-256 hexadecimal do JSON do
    fingerprint com `sort_keys=True` e `ensure_ascii=False`, codificado em UTF-8
    (mesma regra do exemplo em `implementacao_cahce.md`).
- Exportar as funções em `app/application/cache/__init__.py`.
- O prefixo de namespace do Redis (`rag_answer_cache:`) **não** entra aqui; ele é responsabilidade
  do repositório (tarefa 3.0). `build_cache_key` retorna apenas o hash.
- Funções síncronas e puras: sem I/O, sem estado global.
</requirements>

## Subtarefas

- [x] 2.1 Criar `CacheFingerprint` em `app/domain/cache.py` e exportá-lo.
- [x] 2.2 Implementar `normalize_question_finger_print`.
- [x] 2.3 Implementar `build_fingerprint` e `build_cache_key`.
- [x] 2.4 Criar o pacote `app/application/cache/` com `__init__.py` exportando as funções.
- [x] 2.5 Testes de unidade.
- [x] 2.6 Teste de integração com a configuração real.

## Detalhes de Implementação

- Exemplo de referência das funções: `../../.mine/implementacao_cahce.md`, bloco "Exemplo de classe para
  carregar finger-print". A diferença é que o fingerprint é um modelo tipado, não um `dict`
  (regra de tipagem do `CLAUDE.md`). Use `fingerprint.model_dump()` para serializar.
- Regra de normalização e decisão sobre `model_capability`: `tasks/cache/tasks.md`, "Regras de negócio decididas".

## Critérios de Sucesso

- A mesma pergunta com a mesma configuração sempre gera a mesma chave.
- `"  Onde posso COMER?\n"` e `"onde posso comer?"` geram a mesma chave.
- Mudar qualquer um entre `prompt_version`, `rules_version` e `model_capability` gera uma chave diferente.
- A chave é uma string hexadecimal de 64 caracteres.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/cache/test_fingerprint.py`):
  - `normalize_question_finger_print`: espaços nas pontas, maiúsculas, espaços/quebras múltiplas, acentos removidos.
  - `build_fingerprint` preenche os quatro campos a partir da config e da pergunta normalizada.
  - `build_cache_key` é determinística e tem 64 caracteres hexadecimais.
  - Perguntas equivalentes após a normalização → mesma chave.
  - Mudar cada campo de versão → chave diferente (um teste por campo, ou parametrizado).
  - Perguntas diferentes → chaves diferentes.
- [x] Testes de integração (`tests/integration/cache/test_fingerprint_integration.py`):
  - Gerar a chave usando `finger_print` carregado do `env.example.json` real (via loader).
- [x] Testes E2E: não aplicável.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/cache.py` (novo)
- `app/domain/__init__.py`
- `app/application/cache/__init__.py` (novo)
- `app/application/cache/fingerprint.py` (novo)
- `app/infrastructure/config/models.py` (`FingerPrintConfig`, da tarefa 1.0)
- `tests/unit/cache/test_fingerprint.py` (novo)
- `tests/integration/cache/test_fingerprint_integration.py` (novo)
- `tests/unit/domain/test_no_infrastructure_imports.py` (deve continuar passando)
