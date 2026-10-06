# Tarefa 3.0: Serviço de Integração OpenAI

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar o serviço assíncrono de integração com a OpenAI, responsável por três capacidades:
(1) verificação de conteúdo inapropriado/ofensivo das informações do cliente, (2) geração de
embeddings (de chunks e de uma pergunta isolada) e (3) geração da resposta de chat baseada no
histórico e nos trechos similares. Depende das Tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/instructions/open_ai_request.md`
- `.agents/code_patterns/error-handling.md` (timeouts, exceções específicas)
- `.agents/code_patterns/security.md` (api_key via env, timeouts obrigatórios)
- `.agents/code_patterns/python-conventions.md`
</skills>

<requirements>
- Método de moderação: dado os dados do cliente, retornar se há insulto/conteúdo inadequado (contrato JSON `insult`), para interromper a ingestão.
- Método de embeddings a partir de lista de chunks → lista de `{text, vector}`.
- Método de embeddings a partir de uma pergunta → `list[float]`.
- Método de resposta de chat usando `input_guide` + histórico + pergunta + trechos.
- Parâmetros (modelos, `input_guide`) vêm da configuração (Tarefa 1.0), nunca hardcoded.
- Métodos assíncronos, tipados, com timeout e exceções de domínio (`OpenIaException`).
- Nunca logar a API key nem conteúdo sensível.
</requirements>

## Subtarefas

- [ ] 3.1 Cliente/wrapper OpenAI configurável a partir da config.
- [ ] 3.2 Verificação de conteúdo inapropriado (contrato `insult`).
- [ ] 3.3 Geração de embeddings (chunks e pergunta).
- [ ] 3.4 Geração de resposta de chat (histórico + trechos).
- [ ] 3.5 Testes de unidade (com mock do cliente OpenAI).
- [ ] 3.6 Testes de integração do serviço (cliente fake/mocked, sem chamadas reais).

## Detalhes de Implementação

Ver exemplos em `tasks/techspec.md`: moderação (§1.1), embeddings (§1.4, §2.2), pergunta de
chat e `model_historic` (§2.4). Melhorar os exemplos conforme as convenções do projeto.
**Não fazer chamadas reais à OpenAI nos testes.**

## Critérios de Sucesso

- Moderação sinaliza corretamente conteúdo ofensivo.
- Embeddings e respostas retornam os tipos esperados.
- Falhas da API viram exceções de domínio; nenhum detalhe interno exposto.
- Linter e type checker passam.

## Testes da Tarefa

- [ ] Testes de unidade
- [ ] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/openai/` (novo)
- `requirements.txt` (adicionar `openai`)
- `tests/unit/openai/`, `tests/integration/openai/`
