# Tarefa 2.0: Modelos de Domínio e Exceções

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Definir os modelos tipados (pydantic) e as exceções de domínio usados por toda a aplicação:
requisição de cadastro de empresa, payloads de busca (WhatsApp e chat online), itens de
histórico de mensagem, `PayloadQuestionOpenIA` e registros de embedding. Também criar as
exceções de domínio específicas (sem vazar detalhes internos). Depende da Tarefa 1.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/python-conventions.md` (tipagem, nomes)
- `.agents/code_patterns/error-handling.md` (exceções de domínio)
- `.agents/code_patterns/architecture.md` (domínio independente de framework)
</skills>

<requirements>
- Modelo de requisição de cadastro: `user_code` + dados da empresa (`name`, `descricao`, `email`, `address`, `telephone`, `detalhes`) — ver exemplo no techspec.
- Modelos de payload de busca: WhatsApp (`number`, `text`, ...) e chat online (`message`, `user_code`, `user_ip`).
- Modelo de item de histórico de mensagem (papel usuário/assistente + texto) e `PayloadQuestionOpenIA` (pergunta + histórico).
- Modelo de registro de embedding (`text` + `vector`).
- Exceções de domínio (ex.: `OpenIaException`, erro de conteúdo inapropriado, erro de rate limit).
- Modelos de domínio NÃO devem importar FastAPI/boto3/clientes externos.
- Tipagem completa; validação no boundary (pydantic).
</requirements>

## Subtarefas

- [x] 2.1 Modelos de requisição/resposta de cadastro de empresa.
- [x] 2.2 Modelos de payload de busca (WhatsApp e chat online).
- [x] 2.3 Modelos de histórico de mensagem, `PayloadQuestionOpenIA` e embedding.
- [x] 2.4 Exceções de domínio.
- [x] 2.5 Testes de unidade de validação dos modelos.
- [x] 2.6 Testes de integração (serialização via FastAPI/`ApiResponse`).

## Detalhes de Implementação

Ver os exemplos de JSON de entrada (cadastro, chat online, WhatsApp) e o `PayloadQuestionOpenIA`
em `tasks/techspec.md` (seções 1, 2, 2.4, 3). Reutilizar o envelope existente
`app/api/patterns/response.py::ApiResponse` para respostas.

## Critérios de Sucesso

- Payloads válidos passam; inválidos são rejeitados com erro claro.
- Nenhuma dependência de infraestrutura nos modelos de domínio.
- Linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/api/schemas.py` (schemas de API — atualmente vazio)
- `app/domain/` (modelos e exceções de domínio — novo)
- `tests/unit/domain/`
