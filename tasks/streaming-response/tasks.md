# Resumo de Tarefas de Implementação de Respostas em Array e StreamingResponse

As tarefas estão ordenadas por dependência: cada uma só começa depois das que ela usa. Cada tarefa é
uma entrega funcional e incremental, com seus próprios testes.

**Fonte dos requisitos:** `../../meus_prompts/array_response_e_streaming_response.md` (raiz do repositório).
**Cache exato e semântico existentes:** `tasks/cache/tasks.md`, `tasks/semantic-cache/tasks.md`
e `tasks/semantic-cache-threshold/tasks.md`.
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa só referenciam esses documentos e não repetem a implementação.

## Regras de negócio decididas

- **Formato da resposta da LLM:** sempre `{"respostas": ["...", "..."]}`, representado no
  domínio pelo modelo tipado `ChatAnswer` (`respostas: list[str]`).
  - Um array vazio (ou só com textos vazios ou em branco) significa **"não encontrado"**.
  - Cumprimentos ("oi", "obrigado") também vêm em JSON, com um único item.
- **JSON forçado na OpenAI:** a chamada da Responses API usa o formato de texto `json_object`.
  O prompt (`app/domain/prompts.py`) deve exigir o JSON em **todas** as respostas.
- **JSON inválido mesmo com o modo forçado:** registrar com `logger.error`, sem logar o conteúdo
  da resposta, e tratar como "não encontrado" (`ChatAnswer(respostas=[])`). Nada é gravado em cache.
- **Cache exato (Redis):** grava o JSON serializado do `ChatAnswer`. Na leitura, o JSON é
  convertido de volta em `ChatAnswer`.
- **Cache semântico (PostgreSQL):** o campo `response` grava o mesmo JSON. O embedding gravado
  continua sendo o da **pergunta normalizada**, já calculado uma única vez no fluxo.
- **Vários matches semânticos acima do threshold:** os arrays de todos os matches aceitos são
  **mesclados**, sem itens duplicados (texto idêntico aparece uma vez) e mantendo a ordem: o match
  mais similar primeiro, depois a ordem interna de cada array. O JSON mesclado é gravado no Redis.
- **Política de cache:** um `ChatAnswer` sem itens úteis **não** é cacheável.
- **Invalidação do cache antigo:** as entradas atuais estão em texto puro. Incrementar
  `fingerprint.prompt_version` em `env.json` e `env.example.json` (`1.0.0` → `2.0.0`), o que
  muda todas as chaves do fingerprint.
- **Histórico (Redis):** a mensagem do assistente grava os itens **unidos por `"\n\n"`**, em texto
  legível e sem JSON. Uma resposta vazia não é gravada, como já acontece hoje.
- **Mensagens enviadas ao cliente:**
  - com itens: primeiro a introdução aleatória (`_ANSWER_MESSAGES`), depois um evento por item;
  - sem itens: um único evento com uma mensagem aleatória de `_NOT_FOUND_MESSAGES`.
- **Streaming (SSE):**
  - `StreamingResponse` com `media_type="text/event-stream"` e os headers
    `Cache-Control: no-cache` e `X-Accel-Buffering: no`;
  - cada evento tem o formato `data: {"message": "<texto>"}\n\n`, com o JSON gerado por `json.dumps`;
  - o intervalo entre eventos é a constante `STREAM_DELAY_SECONDS = 0.5`. Não há espera antes do
    primeiro evento nem depois do último.
- **Ordem do fluxo:** o `SearchService` resolve **toda** a resposta (cache, RAG, LLM, gravações e
  histórico) **antes** de o stream começar, e o gerador SSE só emite as mensagens já prontas.
  Assim, erros como rate limit e falha da OpenAI continuam virando o envelope `ApiResponse` dos
  handlers globais, porque o status HTTP ainda não foi enviado.
- **Logs:** seguem a regra atual. Nunca logar pergunta, resposta, embedding nem o JSON da LLM.
  Pode-se logar a quantidade de itens.

## Fora de escopo

- Streaming token a token da OpenAI: o stream envia itens já gerados, não tokens.
- Tornar `STREAM_DELAY_SECONDS` configurável via `env.json`, já que o documento pede uma constante.
- Mudanças em SQL, no schema do PostgreSQL ou no Pinecone.
- Migrar entradas antigas de cache: elas são invalidadas pela mudança de `prompt_version`.

## Tarefas

- [x] 1.0 Modelo de domínio `ChatAnswer` (resposta em array)
- [x] 2.0 OpenAI com saída JSON forçada retornando `ChatAnswer`
- [x] 3.0 `SearchService` com resposta em array e caches em JSON
- [x] 4.0 Rotas `/chat` e `/whatsapp` com `StreamingResponse`
