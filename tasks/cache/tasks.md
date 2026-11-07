# Resumo de Tarefas de Implementação do Cache de Respostas por Fingerprint

Tarefas ordenadas por dependência (dependências antes dos dependentes). Cada tarefa é um
entregável funcional incremental com seus próprios testes.

**Fonte dos requisitos:** `../../.mine/implementacao_cahce.md` (raiz do repositório).
**Contexto técnico geral:** `tasks/prd.md` (seção "Busca de informações") e `tasks/techspec.md`
(itens 2 e 3 — fluxo de busca WhatsApp e chat online; 2.1/3.2 histórico no Redis).
Os arquivos de tarefa apenas referenciam esses documentos — não repetem a implementação.

## Regras de negócio decididas

- **Fingerprint** = `prompt_version` + `rules_version` + `model_capability` + texto normalizado da pergunta.
  - `prompt_version`, `rules_version` e `model_capability` vêm da nova seção `finger_print` de
    `env.json` / `env.example.json` (chaves `dev` e `prod`).
  - `model_capability` entra no hash **como a string configurada** (ex.: `"economic"`), sem
    consultar `open_ai.models`.
- **Chave do Redis** = SHA-256 do fingerprint serializado em JSON (`sort_keys=True`,
  `ensure_ascii=False`), com prefixo de namespace (ex.: `rag_answer_cache:{hash}`).
  **Valor** = texto da resposta.
- **Normalização da pergunta:** remover espaços nas pontas, converter para minúsculas e colapsar
  espaços/quebras de linha internas em um único espaço. Acentos são removidos.
- **Expiração (TTL deslizante):** toda chave é gravada com TTL de 24h e o TTL é **renovado a cada
  cache hit**. Chave consultada pelo menos uma vez a cada 24h nunca expira; chave pouco
  consultada expira sozinha.
- **Invalidação manual:** somente por mudança de versão no `env.json` (`prompt_version`,
  `rules_version` ou `model_capability`). As chaves antigas deixam de ser lidas e expiram em 24h.
  **Não** haverá endpoint de limpeza.
- **Cache hit:** a resposta é devolvida sem chamar OpenAI (embedding e chat) nem Pinecone, mas a
  pergunta e a resposta **continuam sendo gravadas no histórico** do usuário.
- **Escrita no cache:** respostas vazias (ou só com espaços) **não** são cacheadas. Quando a
  pergunta não está na base, a LLM devolve resposta vazia (`INPUT_GUIDE` em `app/domain/prompts.py`).
- **Mensagens aleatórias na resposta ao usuário:** depois de gravar o histórico, o `SearchService`
  (`app/application/search/service.py`) decora a resposta com uma mensagem sorteada (`random.choice`):
  - resposta com conteúdo → uma introdução de `_ANSWER_MESSAGES` + `"\n\n"` + a resposta;
  - resposta vazia (ou só com espaços) → uma mensagem de `_NOT_FOUND_MESSAGES` no lugar da resposta.
  O histórico, o Redis e o PostgreSQL guardam **sempre a resposta pura**, sem a mensagem; por isso
  um cache hit também recebe uma introdução nova a cada requisição. Nos testes, as tuplas são
  substituídas por uma única mensagem fixa (fixture `_fixed_search_messages`) para manter o
  resultado determinístico.
- **O cache é compartilhado entre os canais** (WhatsApp e chat online): a chave não depende do
  canal nem do usuário.
- **Falha do Redis não derruba a requisição:** erro na leitura = cache miss; erro na escrita =
  apenas log. Mesmo padrão de `RedisHistoryRepository`.
- **Logs:** registrar hit, miss, gravação e falhas. Nunca registrar o texto da pergunta nem o
  `user_code`; usar apenas um prefixo curto do hash (ex.: 8 caracteres).

## Fora de escopo (ponto de atenção)

- **O histórico da conversa não faz parte do fingerprint.** A mesma pergunta com históricos
  diferentes recebe a mesma resposta cacheada. Isso é aceito pelo requisito, que define o
  fingerprint só com os 4 campos acima.
- **Mudanças no conteúdo do Pinecone** (empresa cadastrada ou excluída) não invalidam o cache
  automaticamente. A resposta antiga pode ser servida até expirar ou até um bump de versão.
- Endpoint de limpeza de cache e contador de hits/PERSIST não serão implementados.

## Tarefas

- [x] 1.0 Configuração `finger_print`
- [x] 2.0 Geração do fingerprint e da chave de cache
- [x] 3.0 Repositório de cache de respostas no Redis
- [x] 4.0 Cache no `SearchService` e injeção de dependências
