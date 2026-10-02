# Tarefa 4.0: Integração OpenAI (embeddings, chat, categorização)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o serviço assíncrono de integração com a OpenAI responsável por: gerar embeddings (de chunks e de mensagens do usuário), categorizar a empresa do cliente (reutilizando ou criando categoria) e gerar a resposta final do chat com base nos trechos mais similares e no histórico.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/security.md` (API key via env) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- API key da OpenAI sempre via variável de ambiente.
- Modelos e `input_guide` vindos do arquivo de configuração (`arquivo_configuracoes.md`): `model_embeddings`, `model_chat`, `input_guide`.
- Gerar embeddings de forma assíncrona para listas de chunks e para a mensagem do usuário.
- Categorizar empresa consultando as categorias existentes; sinalizar necessidade de criar nova categoria quando não houver boa correspondência.
- Detectar conteúdo agressivo/ofensivo e sinalizar para interromper o fluxo de cadastro.
- Montar o payload de chat conforme `.agents/instructions/open_ai_request.md`.
</requirements>

## Subtarefas

- [ ] 4.1 Implementar cliente/serviço OpenAI assíncrono configurável (modelos e key a partir da config/env).
- [ ] 4.2 Implementar geração de embeddings (chunks e mensagem).
- [ ] 4.3 Implementar categorização da empresa (dadas as categorias existentes) e detecção de conteúdo agressivo.
- [ ] 4.4 Implementar geração de resposta de chat usando `input_guide` + histórico + trechos (payload de `open_ai_request.md`).

## Detalhes de Implementação

Fluxo de categorização, criação de categoria e parada por conteúdo agressivo em `techspec.md` e `fluxo_mermaid.md`. Estrutura do payload de chat em `.agents/instructions/open_ai_request.md`. Modelos e `input_guide` em `.agents/instructions/arquivo_configuracoes.md`.

## Critérios de Sucesso

- Embeddings gerados a partir de texto de entrada.
- Categorização retorna categoria existente ou indica criação de nova.
- Conteúdo agressivo é detectado e sinalizado.
- Resposta de chat gerada respeitando o `input_guide`.

## Testes da Tarefa

- [ ] Testes de unidade (montagem de payload, seleção de modelo, tratamento de categorização/agressividade — com cliente OpenAI mockado)
- [ ] Testes de integração (serviço integrado ao carregador de config; sem chamadas reais à OpenAI — usar mocks/fakes)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/external_services/openai/`
- `app/infrastructure/config/`
- `tests/unit/services/`
