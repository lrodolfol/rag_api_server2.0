# Tarefa 8.0: Funcionalidade de Cadastro de Empresa

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Entregar o fluxo completo de cadastro de empresa/negócio: um endpoint que recebe os dados do
cliente e orquestra moderação → normalização → chunking → embeddings → upsert no Pinecone +
gravação no bucket S3. Reutiliza as Tarefas 3.0, 4.0, 5.0 e 6.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/api.md` (rotas em `app/api/routes`, envelope de resposta, handler fino)
- `.agents/code_patterns/architecture.md` (handler fino → service)
- `.agents/code_patterns/error-handling.md`
</skills>

<requirements>
- Endpoint POST que recebe `user_code` + dados da empresa (modelo da Tarefa 2.0).
- Serviço de aplicação orquestrando: moderação (parar se ofensivo) → normalizar → chunk → embeddings → delete+upsert no Pinecone → gravar no bucket.
- Se a moderação detectar conteúdo ofensivo, interromper e responder adequadamente.
- Handler fino: apenas delega ao serviço; resposta no envelope `ApiResponse`.
- Assíncrono, tipado; reutilizar serviços existentes (não duplicar lógica).
</requirements>

## Subtarefas

- [x] 8.1 Serviço de aplicação de ingestão orquestrando o fluxo 1.
- [x] 8.2 Rota POST de cadastro em `app/api/routes` (handler fino).
- [x] 8.3 Tratamento do caso de conteúdo ofensivo (interrupção + resposta).
- [x] 8.4 Testes de unidade do serviço (dependências mockadas).
- [x] 8.5 Testes de integração do endpoint (via `httpx`/`TestClient`, dependências fake).

## Detalhes de Implementação

Ver o fluxo em `tasks/techspec.md` §1 a §1.6 e no PRD ("Cadastro de empresa/negócio").
Manter cada método com menos de 30 linhas e a lógica segregada por responsabilidade.

## Critérios de Sucesso

- Cadastro válido persiste vetores no Pinecone e o arquivo no bucket.
- Conteúdo ofensivo interrompe o fluxo sem persistir.
- Atualização de um mesmo `user_code` substitui os vetores anteriores.
- Linter, type checker e testes passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (se aplicável) — cadastro → verificação de persistência (mock)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/registration/` (novo serviço)
- `app/api/routes/registration.py` (nova rota)
- `app/api/dependencies.py` (injeção dos serviços)
- `tests/unit/registration/`, `tests/integration/api/`
