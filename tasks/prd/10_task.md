# Tarefa 10.0: Integração da Aplicação e Tratamento de Erros

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Finalizar a aplicação como um todo: centralizar a injeção de dependências, registrar todas as
rotas no app factory, adicionar os exception handlers globais que mapeiam as exceções de
domínio para o envelope `ApiResponse` (sem vazar detalhes internos) e cobrir os fluxos
ponta-a-ponta com testes de integração. Depende das Tarefas 8.0 e 9.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/api.md` (dependências em `app/api/dependencies.py`, health-check)
- `.agents/code_patterns/error-handling.md` (handlers, sem vazar interno)
- `.agents/code_patterns/security.md` (mensagens seguras ao cliente)
- `.agents/code_patterns/architecture.md`
</skills>

<requirements>
- Injeção de dependências centralizada em `app/api/dependencies.py` (config + serviços).
- Registrar as rotas de cadastro, WhatsApp e chat online no `create_app` (além de health).
- Exception handlers globais convertendo exceções de domínio em `ApiResponse` com `status_code`/`message`/`errors`, sem stack traces nem dados sensíveis.
- Rate limit da aplicação conforme `api.md` (segurança).
- Testes de integração ponta-a-ponta dos três fluxos (dependências externas fake/mock).
</requirements>

## Subtarefas

- [ ] 10.1 Centralizar DI em `app/api/dependencies.py`.
- [ ] 10.2 Registrar todos os routers no app factory (`app/main.py`).
- [ ] 10.3 Exception handlers globais → envelope `ApiResponse`.
- [ ] 10.4 Testes de integração E2E dos fluxos de cadastro e busca.
- [ ] 10.5 Rodar lint, type check e toda a suíte de testes.

## Detalhes de Implementação

Reutilizar o factory existente em `app/main.py::create_app` e o envelope
`app/api/patterns/response.py::ApiResponse`. Seguir o padrão de resposta de erro de
`.agents/code_patterns/api.md` e `.agents/code_patterns/error-handling.md`. Não expor
detalhes internos (ver `security.md`).

## Critérios de Sucesso

- Todas as rotas acessíveis; `/health` continua funcionando.
- Erros de domínio retornam respostas seguras e padronizadas.
- Testes E2E dos três fluxos passam com dependências mockadas.
- Linter, type checker e suíte completa passam.

## Testes da Tarefa

- [ ] Testes de unidade
- [ ] Testes de integração
- [ ] Testes E2E (fluxos de cadastro, WhatsApp e chat online)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/main.py` (registro de rotas + handlers)
- `app/api/dependencies.py` (DI central)
- `app/api/errors/` (exception handlers — novo)
- `tests/integration/api/`
