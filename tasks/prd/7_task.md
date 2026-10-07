# Tarefa 7.0: Histórico no Redis + Rate Limiter em memória

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar a infraestrutura de histórico de conversas no Redis (com TTL) e o rate limiter em
memória por IP para o chat online. O histórico usa chaves distintas por canal. Depende das
Tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/architecture.md`
- `.agents/code_patterns/error-handling.md`
- `.agents/code_patterns/security.md` (senha do Redis via env)
- `.agents/code_patterns/python-conventions.md` (constantes para TTL/limites)
</skills>

<requirements>
- Armazenar e recuperar histórico de mensagens no Redis por usuário.
- Chaves por canal: `users_histotic_whatsapp` e `users_histotic_online`.
- TTL do histórico de 30 minutos.
- Rate limiter **em memória** por IP: máximo de 3 mensagens, TTL de 5 horas.
- Conexão Redis configurada via config (senha via variável de ambiente).
- Métodos assíncronos/tipados; limites e TTLs como constantes/config.
</requirements>

## Subtarefas

- [x] 7.1 Store de histórico no Redis (get/append) com TTL de 30 min e chaves por canal.
- [x] 7.2 Rate limiter em memória por IP (limite 3, TTL 5h) com mensagem de bloqueio padronizada.
- [x] 7.3 Testes de unidade do rate limiter (contagem, expiração).
- [x] 7.4 Testes de unidade/integração do histórico (Redis fake, ex.: `fakeredis`).

## Detalhes de Implementação

Ver `tasks/techspec.md` §2.1 (chave WhatsApp), §3.1 (bloqueio por IP, 5h) e §3.2 (chave online).
TTL de 30 min do histórico conforme PRD ("Busca de informações"). A resposta de bloqueio deve
seguir o padrão de API (`.agents/code_patterns/api.md`, envelope `ApiResponse`).

## Critérios de Sucesso

- Histórico expira após 30 min; canais isolados por chave.
- IP é bloqueado após 3 mensagens; libera após 5h.
- Nenhuma senha logada.
- Linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/redis/` e `app/infrastructure/rate_limit/` (novos)
- `requirements.txt` (adicionar `redis`; `fakeredis` para testes)
- `tests/unit/redis/`, `tests/unit/rate_limit/`
