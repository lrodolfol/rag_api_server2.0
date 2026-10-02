# Tarefa 1.0: Fundação do projeto (arquitetura, configuração, logging, bootstrap FastAPI)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Estabelecer o esqueleto da aplicação seguindo a clean architecture do projeto, o carregador de configuração (JSON por ambiente + variáveis de ambiente para dados sensíveis), o logging estruturado e o bootstrap do FastAPI com o endpoint `/health` funcionando. É a base sobre a qual todas as outras tarefas serão construídas.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica a esta tarefa (as skills existentes são de criação de PRD/tasks e geração de conteúdo, não de implementação). Seguir os padrões de `.agents/code_patterns/architecture.md` e `.agents/code_patterns/python-conventions.md`.
</skills>

<requirements>
- Criar as camadas `domain/`, `application/`, `infrastructure/` e `api/` dentro de `app/`.
- Carregador de configuração tipado lendo o JSON de `dev`/`prod` conforme `.agents/instructions/arquivo_configuracoes.md`.
- Valores sensíveis (API keys, senhas, secrets) SEMPRE vêm de variáveis de ambiente (`.env`), nunca hardcoded.
- Logging via `logging` (sem `print`).
- Aplicação FastAPI inicializável com `python main.py` (ou equivalente) e endpoint `/health` respondendo.
- Todo código assíncrono e tipado.
</requirements>

## Subtarefas

- [x] 1.1 Criar a estrutura de pastas das camadas (`domain/`, `application/`, `infrastructure/`, `api/`) com `__init__.py`.
- [x] 1.2 Implementar carregador de configuração tipado (seleção dev/prod por `ENVIRONMENT`, segredos via env vars).
- [x] 1.3 Configurar logging central da aplicação (substituindo o `print` atual de `app/main.py`).
- [x] 1.4 Implementar o bootstrap do FastAPI e registrar a rota `/health`.
- [x] 1.5 Garantir execução dentro do `.venv` e atualização do `requirements.txt`.

## Detalhes de Implementação

Ver `techspec.md` (arquitetura do sistema) e `.agents/code_patterns/architecture.md` (separação de camadas e injeção de dependência). O formato da configuração está em `.agents/instructions/arquivo_configuracoes.md`. Variáveis de ambiente disponíveis em `.env.example`.

## Critérios de Sucesso

- `GET /health` retorna status de sucesso.
- Configuração carregada conforme `ENVIRONMENT`, sem segredos no código.
- Logs emitidos via logger (nenhum `print` na aplicação).
- Estrutura de camadas criada e importável.

## Testes da Tarefa

- [x] Testes de unidade (carregador de configuração: seleção de ambiente e leitura de env vars)
- [x] Testes de integração (endpoint `/health` via cliente de teste do FastAPI)
- [ ] Testes E2E (não aplicável a esta tarefa)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/main.py`, `main.py`
- `app/infrastructure/config/` (novo)
- `app/api/routes/health.py`
- `.env`, `.env.example`, `requirements.txt`
- `tests/unit/`, `tests/integration/`
