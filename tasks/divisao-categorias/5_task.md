# Tarefa 5.0: Integração da categoria no cadastro (`RegistrationService`)

<critical>Ler os arquivos `divisao_em_categorias.md` (raiz), `tasks/divisao-categorias/tasks.md`, `tasks/prd.md` e `tasks/techspec.md`, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Esta tarefa liga as peças das tarefas 1.0 a 4.0 no fluxo de cadastro. O cadastro passa a:

1. ler as categorias do Redis;
2. moderar e classificar o conteúdo numa única chamada à LLM;
3. resolver a categoria (existente, nova ou `fallback`) e gravar a nova no Redis;
4. ler a categoria antiga do cliente no Pinecone;
5. gerar os embeddings e regravar os vetores com a categoria;
6. remover o registro do arquivo antigo do bucket, se a categoria mudou;
7. gravar o registro no arquivo da categoria nova.

<skills>
### Conformidade com Skills Padrões

- `.claude/code_patterns/architecture.md` (o serviço só coordena, sem lógica de infraestrutura)
- `.claude/code_patterns/python-conventions.md` (métodos com menos de 30 linhas)
- `.claude/code_patterns/error-handling.md`
- `.claude/code_patterns/security.md`
- `.claude/code_patterns/testing.md`
</skills>

<requirements>
- Injetar o `CategoryService` (tarefa 1.0) no `RegistrationService` e atualizar a fábrica em
  `app/api/dependencies.py`.
- O conteúdo inapropriado continua interrompendo o fluxo **antes** de qualquer gravação: nem
  categoria nova no Redis, nem vetores, nem bucket.
- A categoria antiga é lida (`get_category_by_user_code`) **antes** do upsert, porque o upsert
  apaga os vetores antigos do cliente.
- Ordem das gravações: vetores com a categoria nova → remoção do arquivo antigo (só se a categoria
  antiga existir e for diferente da nova) → gravação no arquivo novo.
- Remover os slugs provisórios deixados pelas tarefas 3.0 e 4.0.
- Dividir o fluxo em métodos privados curtos (por exemplo `_moderate_and_classify` e
  `_remove_from_previous_category`). Nenhum método com mais de 30 linhas.
- Registrar em log a categoria definida e se houve mudança de categoria (nunca o `user_code` nem o
  conteúdo).
- Atualizar a docstring do módulo com o novo fluxo.
- O contrato HTTP de `/registration` não muda.
</requirements>

## Subtarefas

- [x] 5.1 Injetar o `CategoryService` e atualizar a fábrica em `dependencies.py`.
- [x] 5.2 Passar as categorias para `moderate` e resolver a categoria com `resolve_or_create`.
- [x] 5.3 Ler a categoria antiga, gravar os vetores com a categoria nova e limpar o arquivo antigo.
- [x] 5.4 Gravar o registro no arquivo da categoria nova e atualizar a docstring.
- [x] 5.5 Criar ou atualizar os testes unitários e de integração.
- [x] 5.6 Rodar os testes, o lint e o type checking dentro do `.venv`.

## Detalhes de Implementação

As regras de categoria nova, `fallback` e mudança de categoria estão em
`tasks/divisao-categorias/tasks.md`, nas seções "Categorias" e "Cadastro". O fluxo original de
cadastro está descrito em `tasks/techspec.md` (item 1).

## Critérios de Sucesso

- Primeiro cadastro de um restaurante: vetores com `category="alimentacao"` e registro em
  `client_services_alimentacao.jsonl`.
- Recadastro do mesmo cliente como salão de beleza: vetores com `category="beleza"`, registro
  removido de `client_services_alimentacao.jsonl` e gravado em `client_services_beleza.jsonl`.
- Recadastro na mesma categoria: nenhuma remoção extra no bucket.
- Categoria sugerida pela LLM e inexistente: adicionada ao Redis e usada no arquivo e nos vetores.
- Conteúdo inapropriado: `InappropriateContentError` e nenhuma gravação.
- A suíte completa passa, sem erros de lint e de type checking.

## Testes da Tarefa

- [x] Testes de unidade (`tests/unit/registration/test_registration_service.py`), com todas as
  dependências mockadas: primeiro cadastro; mudança de categoria; mesma categoria; categoria nova;
  categoria vazia (`fallback`); conteúdo inapropriado sem gravações; ordem das chamadas (leitura
  da categoria antiga antes do upsert).
- [x] Testes de integração (`tests/integration/api/test_registration_api.py`): seguir o padrão
  existente; `POST` de cadastro com a OpenAI mockada devolvendo uma categoria, conferindo o slug
  repassado ao Pinecone e ao storage.
- [x] Testes E2E (`tests/integration/api/test_e2e_flows.py`): ajustar o fluxo de cadastro
  existente para a categoria.

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/registration/service.py`
- `app/api/dependencies.py`
- `app/application/categories/service.py` (só uso)
- `tests/unit/registration/test_registration_service.py`
- `tests/integration/api/test_registration_api.py` e `tests/integration/api/test_e2e_flows.py`
