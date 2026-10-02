# Tarefa 10.0: Endpoints da API (cadastro, WhatsApp, chat online)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Expor os casos de uso via HTTP com FastAPI: endpoint para receber e persistir as informações das empresas/negócios (Tarefa 8), endpoint principal para mensagens vindas da integração com WhatsApp e endpoint para mensagens de chat online (ambos usando a Tarefa 9). Os handlers devem ser finos, delegando aos casos de uso.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/api.md`, `.agents/code_patterns/architecture.md` (handlers finos) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Endpoint de cadastro de empresa/negócio (invoca o caso de uso da Tarefa 8).
- Endpoint principal para mensagens do WhatsApp (invoca o caso de uso da Tarefa 9).
- Endpoint para mensagens de chat online (invoca o caso de uso da Tarefa 9).
- Handlers finos (sem lógica de negócio), usando injeção de dependência.
- Resposta expõe os 5 resultados formatados (cada resultado em uma mensagem, com links de contato); não vazar detalhes internos nos erros.
- Usar os schemas da Tarefa 2.
</requirements>

## Subtarefas

- [ ] 10.1 Implementar o endpoint de cadastro de empresa/negócio.
- [ ] 10.2 Implementar o endpoint de mensagens do WhatsApp.
- [ ] 10.3 Implementar o endpoint de chat online.
- [ ] 10.4 Configurar injeção de dependências e registrar as rotas na aplicação.

## Detalhes de Implementação

Endpoints requeridos em `prd.md` (seção "Funcionalidades Principais") e formato de exibição do resultado na seção "Exibição do resultado". Padrão de handler fino + injeção em `.agents/code_patterns/architecture.md` e `.agents/code_patterns/api.md`. Casos de uso nas Tarefas 8 e 9; schemas na Tarefa 2.

## Critérios de Sucesso

- Os três endpoints respondem e delegam corretamente aos casos de uso.
- A busca retorna até 5 resultados formatados com links de contato.
- Erros tratados sem expor detalhes internos.

## Testes da Tarefa

- [ ] Testes de unidade (validação de contrato dos handlers com casos de uso mockados)
- [ ] Testes de integração (chamadas HTTP via cliente de teste do FastAPI para os três endpoints)
- [ ] Testes E2E (fluxo cadastro → busca retornando resultados, com infraestrutura de teste isolada)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/api/routes/` (cadastro, whatsapp, chat)
- `app/api/schemas.py`, `app/api/dependencies.py`
- `app/main.py`
- `tests/integration/api/`
