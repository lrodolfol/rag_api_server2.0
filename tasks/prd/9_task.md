# Tarefa 9.0: Funcionalidade de Busca (WhatsApp + Chat Online)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Entregar a busca por RAG através de um **serviço de busca compartilhado** (histórico →
embeddings da pergunta → consulta Pinecone com similaridade > 0.9 → resposta via OpenAI)
exposto por dois endpoints: integração WhatsApp e chat online. O chat online aplica
adicionalmente o rate limit por IP em memória. Reutiliza as Tarefas 3.0, 5.0 e 7.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/api.md` (envelope de resposta, handlers finos, rate limit)
- `.agents/instructions/open_ai_request.md`
- `.agents/code_patterns/architecture.md`
- `.agents/code_patterns/error-handling.md`
</skills>

<requirements>
- Serviço de busca compartilhado usado pelos dois endpoints (sem duplicar o pipeline).
- Endpoint WhatsApp: payload do techspec; histórico na chave `users_histotic_whatsapp`.
- Endpoint chat online: payload do techspec; histórico na chave `users_histotic_online`; aplicar rate limit por IP (máx 3, TTL 5h) antes de processar, respondendo bloqueio no envelope padrão quando excedido.
- Gerar embeddings da pergunta, consultar Pinecone (similaridade > 0.9) e perguntar à OpenAI com histórico + trechos.
- Atualizar o histórico do usuário após a resposta (TTL 30 min).
- Resultados devem permitir link para e-mail, telefone e WhatsApp quando existirem (PRD).
- Handlers finos; respostas no envelope `ApiResponse`.
</requirements>

## Subtarefas

- [x] 9.1 Serviço de busca compartilhado (histórico → embeddings → Pinecone → OpenAI).
- [x] 9.2 Endpoint WhatsApp (chave de histórico própria).
- [x] 9.3 Endpoint chat online (chave própria + rate limit por IP).
- [x] 9.4 Atualização do histórico pós-resposta (TTL 30 min).
- [x] 9.5 Testes de unidade do serviço de busca (dependências mockadas).
- [x] 9.6 Testes de integração dos dois endpoints, incluindo o caso de bloqueio por rate limit.

## Detalhes de Implementação

Ver `tasks/techspec.md` §2 (WhatsApp) e §3 (chat online), reutilizando os exemplos de
embeddings (§2.2/§3.3), query (§2.3/§3.4) e pergunta à OpenAI (§2.4/§3.5). O corte de
similaridade 0.9 vem do PRD. Reutilizar a Tarefa 7.0 para histórico e rate limit.

## Critérios de Sucesso

- Ambos os endpoints retornam respostas baseadas nos itens mais similares (> 0.9).
- Chat online bloqueia após 3 mensagens do mesmo IP com resposta padronizada.
- Histórico isolado por canal e expira em 30 min.
- Linter, type checker e testes passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (se aplicável) — pergunta → resposta (dependências mock)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search/` (novo serviço compartilhado)
- `app/api/routes/whatsapp.py`, `app/api/routes/chat.py` (novas rotas)
- `app/api/dependencies.py` (injeção)
- `tests/unit/search/`, `tests/integration/api/`
