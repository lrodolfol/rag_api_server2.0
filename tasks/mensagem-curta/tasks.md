# Resumo de Tarefas de Implementação de Identificação de Mensagem Curta

As tarefas estão ordenadas por dependência. Cada uma é uma entrega funcional e incremental, com
seus próprios testes.

**Fonte dos requisitos:** `identificar_mensagem_curta.md` (raiz do repositório).
**Fluxo de busca e streaming atuais:** `tasks/streaming-response/tasks.md`.
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa só referenciam esses documentos e não repetem a implementação.

## Regras de negócio decididas

- **Sem LLM:** a identificação é feita só com código local (biblioteca padrão). Ela não chama a
  OpenAI, não gera embedding e não adiciona dependências.
- **Regra de mensagem curta:** uma mensagem é curta quando tem **menos de 2 letras**.
  - Contam como letra os caracteres alfabéticos Unicode, inclusive os acentuados (`á`, `ç`, `ñ`).
  - **Não** contam: espaços, números, pontuação, símbolos e emojis.
  - Essa regra resolve uma contradição do documento original. A definição fala em "menos de 1
    palavra ou menos de 2 caracteres", mas os exemplos `"1234"` e `"!!"` são curtos mesmo tendo 2
    ou mais caracteres. Por isso, só letras contam.
  - Exemplos de mensagem **curta** (`True`): `"..."`, `"i"`, `"!!"`, `"1234"`, `" "`, `"   "`,
    `"a1"`, `"é?"`, `"😀😀"`.
  - Exemplos de mensagem **válida** (`False`): `"oi"`, `"ok"`, `"  oi  "`, `"pizzaria no centro"`,
    `"onde tem açaí?"`.
- **Ponto de verificação:** no início de `SearchService.search`, **antes** de fingerprint, cache
  exato, embedding, cache semântico, histórico, Pinecone e OpenAI.
- **Resposta:** uma lista com **uma única** mensagem escolhida aleatoriamente de
  `_INVALID_MESSAGE_RESPONSES`, entregue ao cliente pelo mesmo stream SSE de hoje. Não há
  introdução (`_ANSWER_MESSAGES`) nem mensagem de "não encontrado" (`_NOT_FOUND_MESSAGES`).
- **Histórico e caches:** uma mensagem curta **não** é gravada no histórico (Redis) nem nos caches
  exato e semântico.
- **Rate limit:** continua sendo aplicado antes, na rota `/chat`. Uma mensagem curta também conta
  para o limite.
- **Payloads:** os modelos `OnlineChatSearchPayload` e `WhatsAppSearchPayload` não mudam. Uma
  mensagem vazia (`""`) continua retornando 422 por causa do `min_length=1`.
- **Logs:** registrar que uma mensagem curta foi recebida, com o canal. **Nunca** registrar o
  conteúdo da mensagem.

## Fora de escopo

- Tornar o mínimo de letras configurável via `env.json`. O valor é uma constante do módulo.
- Detectar mensagens sem sentido que tenham 2 letras ou mais (por exemplo, `"asdfgh"`). Esses casos
  continuam indo para o fluxo RAG.
- Mudanças nos contratos HTTP, no formato SSE, em SQL, no Redis ou no Pinecone.

## Tarefas

- [x] 1.0 Detector de mensagem curta (`is_short_message`)
- [x] 2.0 Integração no `SearchService` e documentação
