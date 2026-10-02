# Tarefa 6.0: Histórico de mensagens com Redis (TTL 30 min)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o armazenamento do histórico de conversa do usuário em Redis, com TTL de 30 minutos. O histórico é lido antes de gerar a resposta e regravado (renovando o TTL) após cada interação.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/security.md` (senha via env) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Conexão Redis assíncrona; host/porta/db da config e senha via env (`arquivo_configuracoes.md`, seção `redis`).
- Ler o histórico do usuário (vazio quando não existir).
- Gravar/atualizar o histórico aplicando TTL de 30 minutos.
- Formato do histórico compatível com o payload de chat da OpenAI (lista de mensagens role/content).
</requirements>

## Subtarefas

- [ ] 6.1 Implementar conexão Redis assíncrona a partir da configuração/env.
- [ ] 6.2 Implementar leitura do histórico por usuário.
- [ ] 6.3 Implementar gravação do histórico com TTL de 30 minutos.

## Detalhes de Implementação

Requisito de histórico com TTL de 30 min em `prd.md` (seção "Busca de informações") e `techspec.md`. Formato do histórico no payload em `.agents/instructions/open_ai_request.md` (`historic`). Parâmetros do Redis em `.agents/instructions/arquivo_configuracoes.md`.

## Critérios de Sucesso

- Histórico inexistente retorna vazio sem erro.
- Histórico gravado é recuperável dentro da janela de TTL.
- TTL de 30 min aplicado/renovado a cada gravação.

## Testes da Tarefa

- [ ] Testes de unidade (serialização do histórico e lógica de TTL com cliente Redis mockado/fake)
- [ ] Testes de integração (contra Redis de teste isolado: gravar, ler e verificar expiração)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/messaging/` ou `app/infrastructure/cache/`
- `app/infrastructure/config/`
- `tests/unit/`, `tests/integration/`
