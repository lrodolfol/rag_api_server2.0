# Tarefa 4.0: Invalidação no cadastro/atualização (`RegistrationService`) e injeção de dependências

<critical>Ler os arquivos `../../meus_prompts/invalid-cache-on-new-service.md` (raiz), `tasks/invalidate-cache/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Quando um serviço é cadastrado ou atualizado (`POST /companies`), as respostas já guardadas no
cache semântico para a categoria dele ficam desatualizadas. Esta tarefa faz o
`RegistrationService` (`app/application/registration/service.py`) invalidar a categoria nova e,
quando o cliente mudou de categoria, também a anterior, usando o `SemanticCacheService`. Inclui
a injeção da dependência em `app/api/dependencies.py`. Depende das tarefas 1.0 e 2.0 (a 3.0 é
independente desta, mas sem ela as entradas gravadas ainda não têm categoria).

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (serviço de aplicação orquestra; sem SQL nem `psycopg` aqui)
- `.claude/code_patterns/python-conventions.md` (`register` continua < 30 linhas: extrair helper)
- `.claude/code_patterns/error-handling.md` (falha do cache não derruba o cadastro; já tratada no repositório)
- `.claude/code_patterns/security.md` (logar só slugs; nunca `user_code` nem conteúdo do cliente)
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- `RegistrationService.__init__` ganha o parâmetro `semantic_cache: SemanticCacheService`
  (importado de `app.application.cache`).
- Em `register`, **imediatamente após** `upsert_company_vectors` e **antes** de
  `_remove_from_previous_category` / `save_client`, chamar um helper privado (ex.:
  `_invalidate_semantic_cache(previous_slug, category.slug)`) que:
  1. chama `self._semantic_cache.invalidate_category(category.slug)`;
  2. se `previous_slug` não for `None` e for diferente de `category.slug`, chama também
     `invalidate_category(previous_slug)`.
  - Não chamar duas vezes para a mesma categoria quando ela não mudou.
- Conteúdo rejeitado pela moderação (`InappropriateContentError`) continua **sem nenhuma
  escrita**, inclusive sem invalidação.
- Falha do PostgreSQL na invalidação é logada pelo repositório e o cadastro continua até o
  final (status 201 mantido). O serviço não captura exceções do cache.
- `app/api/dependencies.py`: `get_registration_service` passa
  `semantic_cache=_semantic_cache_service()` (provider já existente e cacheado com `lru_cache`).
- Atualizar a docstring do módulo (lista de passos do fluxo) com o passo de invalidação.
- Logs: `logger.info("Semantic cache invalidated for category '%s'", slug)` pode ficar no
  repositório (tarefa 1.0); no serviço, no máximo um log citando os slugs invalidados.
</requirements>

## Subtarefas

- [ ] 4.1 Receber `semantic_cache` no construtor e guardar em `self._semantic_cache`.
- [ ] 4.2 Criar o helper de invalidação (categoria nova + anterior quando diferente) e chamá-lo
  logo após o upsert.
- [ ] 4.3 Atualizar `get_registration_service` em `app/api/dependencies.py`.
- [ ] 4.4 Atualizar docstring do módulo.
- [ ] 4.5 Atualizar as fixtures/testes existentes que constroem `RegistrationService`
  (`tests/unit/registration/test_registration_service.py`,
  `tests/integration/api/test_registration_api.py`, `tests/integration/api/test_e2e_flows.py`).
- [ ] 4.6 Testes de unidade e de integração da invalidação.

## Detalhes de Implementação

- Fluxo atual de `register` e de `_remove_from_previous_category` (leitura de `previous_slug`
  antes do upsert): `app/application/registration/service.py`.
- Método `invalidate_category` e o que ele apaga (categoria + linhas `NULL`): tarefas 1.0 e 2.0
  e `tasks/invalidate-cache/tasks.md`.
- Ordem das escritas no cadastro: `tasks/divisao-categorias/tasks.md`, seção "Cadastro".

## Critérios de Sucesso

- Primeiro cadastro em `alimentacao` (sem categoria anterior): `invalidate_category` chamado
  uma vez com `"alimentacao"`.
- Recadastro na mesma categoria: chamado uma vez com a categoria.
- Recadastro mudando de `beleza` para `alimentacao`: chamado com `"alimentacao"` **e** com
  `"beleza"` (duas chamadas, uma para cada).
- A invalidação acontece **depois** de `upsert_company_vectors` (ordem verificada com
  `MagicMock.attach_mock`, como em `test_should_read_previous_category_before_upsert_and_write_in_order`).
- Conteúdo inapropriado: `invalidate_category` nunca chamado.
- `POST /companies` responde 201 mesmo quando o PostgreSQL falha na invalidação.
- Todos os testes que já existiam continuam passando.

## Testes da Tarefa

- [ ] Testes de unidade (`tests/unit/registration/test_registration_service.py`, `AsyncMock`
  para `semantic_cache`): os cinco cenários dos critérios acima (primeiro cadastro, mesma
  categoria, mudança de categoria, ordem após upsert, moderação rejeitada) e o teste de logs
  existente ampliado para garantir que `user_code` não aparece nos logs de invalidação.
- [ ] Testes de integração:
  - `tests/integration/api/test_registration_api.py`: serviço com `SemanticCacheService` real
    sobre `semantic_cache_db` (fixture de `tests/integration/conftest.py`); linhas pré-gravadas
    em `alimentacao`, `beleza` e `None` → após `POST /companies` classificado em `alimentacao`,
    restam só as de `beleza`; resposta 201.
  - Falha simulada (`semantic_cache_db.error = psycopg.OperationalError(...)`) → 201 e vetores
    gravados normalmente.
- [ ] Testes E2E (`tests/integration/api/test_e2e_flows.py`): o cenário de mudança de categoria
  (`test_e2e_should_move_client_to_new_category_on_registration_update`) passa a verificar que
  as entradas das **duas** categorias foram apagadas do `semantic_cache_db`.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/registration/service.py`
- `app/api/dependencies.py`
- `tests/unit/registration/test_registration_service.py`
- `tests/integration/api/test_registration_api.py`
- `tests/integration/api/test_e2e_flows.py`
- `tests/integration/conftest.py`
