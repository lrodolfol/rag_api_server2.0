# Resumo de Tarefas de Implementação da Divisão da Base de Conhecimento em Categorias

As tarefas estão ordenadas por dependência: cada uma só começa depois das que ela usa. Cada tarefa é
uma entrega funcional e incremental, com seus próprios testes.

**Fonte dos requisitos:** `../../meus_prompts/divisao_em_categorias.md` (raiz do repositório).
**Fluxos atuais de cadastro, exclusão e busca:** `tasks/delete-service/tasks.md`,
`tasks/streaming-response/tasks.md` e `tasks/mensagem-curta/tasks.md`.
**Contexto técnico geral:** `tasks/prd.md` e `tasks/techspec.md`.
Os arquivos de tarefa só referenciam esses documentos e não repetem a implementação.

## Regras de negócio decididas

### Categorias
- **Nome x slug:** cada categoria tem um **nome** (o texto original, em maiúsculas e com acento,
  por exemplo `SERVIÇOS PROFISSIONAIS`) e um **slug** (sem acento, minúsculo, com `_` no lugar de
  espaços, por exemplo `servicos_profissionais`).
  - O **nome** é o que fica no Redis e o que é mostrado à LLM.
  - O **slug** é o que vai no nome do arquivo do bucket e no metadado `category` do Pinecone.
  - Duas categorias são a mesma quando têm o mesmo slug (`"Alimentação"` = `"ALIMENTACAO"`).
- **Lista inicial:** as 20 categorias de `../../meus_prompts/divisao_em_categorias.md` ficam no arquivo de
  configuração (`env.json` e `env.example.json`), nunca fixas no código.
- **Redis:** as categorias ficam num **SET** do Redis (o nome da chave também vem da configuração).
  A lista inicial é carregada no startup da aplicação (`lifespan`) com `SADD`, que é idempotente:
  reiniciar a aplicação não duplica nem apaga categorias novas.
- **Categoria nova:** quando a LLM sugerir, no cadastro, uma categoria que não existe (comparando
  pelo slug), ela é adicionada ao SET do Redis.
- **Categoria vazia no cadastro:** se a LLM não devolver categoria, o serviço usa a categoria
  reserva definida na configuração (`fallback`, valor inicial `OUTROS`), que também é adicionada
  ao Redis. O cadastro não falha por falta de categoria.
- **Falha no Redis:** a leitura das categorias registra o erro e retorna lista vazia. A escrita
  registra o erro e segue o fluxo. O Redis nunca derruba o cadastro, a busca nem o startup.

### Cadastro
- O prompt de moderação recebe a lista de categorias do Redis e a resposta JSON passa a ter o
  campo `categoria`: `{"insult": bool, "insult_text": str, "categoria": str}`.
- O registro do cliente vai para o arquivo `client_services_{slug}.jsonl` no bucket.
- Cada vetor no Pinecone passa a ter os metadados `text`, `user_code` e **`category`** (slug).
- **Mudança de categoria no recadastro:** antes de regravar os vetores, o serviço lê a categoria
  antiga nos metadados do Pinecone. Se ela for diferente da nova, o registro é removido do arquivo
  antigo do bucket.

### Exclusão
- A categoria do cliente é lida nos metadados do Pinecone **antes** de apagar os vetores. O
  registro é removido do arquivo `client_services_{slug}.jsonl` dessa categoria.
- Se os vetores não tiverem `category` (dados antigos), os vetores são apagados e é registrado um
  `warning`. O arquivo antigo `client_services.jsonl` não é alterado.

### Busca
- Dentro de `SearchService._run_pipeline`, antes de consultar o Pinecone, o serviço pede à LLM a
  categoria mais relevante para a pergunta, entre as categorias do Redis.
- A pergunta é classificada sozinha, sem o histórico.
- **Busca sem filtro (comportamento atual):** é usada quando a lista de categorias está vazia,
  quando a LLM não devolve uma categoria que exista no Redis (comparando pelo slug) ou quando a
  chamada falha (`OpenIaException`). A falha é registrada com `warning` e a busca continua.
- Quando a categoria é válida, a consulta ao Pinecone usa o filtro `{"category": {"$eq": slug}}`.
- A classificação só acontece quando não há resposta nos caches exato e semântico. As chaves e os
  conteúdos dos caches não mudam.
- **Logs:** registrar a categoria escolhida (ou que a busca seguiu sem filtro). **Nunca** registrar
  a pergunta, o conteúdo do cliente nem o `user_code`.

## Fora de escopo

- Migrar os dados antigos: vetores sem `category` e o arquivo `client_services.jsonl`. Esses
  vetores só aparecem na busca sem filtro, até o cliente se recadastrar.
- Remover ou renomear categorias do Redis.
- Expor endpoints HTTP para listar ou gerenciar categorias.
- Mudanças nos contratos HTTP (payloads e respostas) e no formato SSE.

## Tarefas

- [x] 1.0 Catálogo de categorias (domínio, configuração, Redis e carga no startup)
- [x] 2.0 Moderação com classificação da categoria (`OpenAIService.moderate`)
- [x] 3.0 Categoria nos vetores do Pinecone (metadado, filtro e leitura por `user_code`)
- [x] 4.0 Armazenamento do cliente por categoria no bucket S3
- [x] 5.0 Integração da categoria no cadastro (`RegistrationService`)
- [x] 6.0 Integração da categoria na exclusão (`DeletionService`)
- [x] 7.0 Classificação da pergunta e busca filtrada (`SearchService`)
