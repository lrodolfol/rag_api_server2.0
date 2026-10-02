# Tarefa 9.0: Caso de uso — Busca e resposta (RAG)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o caso de uso de busca (RAG): recuperar o histórico do usuário, gerar o embedding da mensagem, consultar a `knowledge_base` por similaridade (top 5), gerar a resposta via OpenAI com base nos trechos e no histórico, formatar os 5 melhores resultados (com links de contato) e regravar o histórico com TTL.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/architecture.md` e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Buscar histórico do usuário (Tarefa 6); vazio quando não existir.
- Gerar embedding da mensagem e consultar top 5 por similaridade (Tarefas 3 e 4).
- Gerar resposta via OpenAI usando `input_guide` + histórico + trechos (payload de `open_ai_request.md`).
- Formatar os 5 melhores resultados, cada um com links de e-mail, telefone e WhatsApp (quando existirem).
- Regravar o histórico com TTL de 30 min após a interação.
- Caso de uso na camada `application`.
</requirements>

## Subtarefas

- [ ] 9.1 Recuperar histórico e gerar embedding da mensagem do usuário.
- [ ] 9.2 Consultar a `knowledge_base` por similaridade (top 5) e gerar a resposta via OpenAI.
- [ ] 9.3 Formatar os 5 resultados com links de contato (e-mail/telefone/WhatsApp).
- [ ] 9.4 Regravar o histórico do usuário com TTL de 30 min.

## Detalhes de Implementação

Fluxo de busca em `techspec.md` (bloco "Usuário -> envia mensagem") e `fluxo_mermaid.md` (nós M→T). Montagem do payload em `.agents/instructions/open_ai_request.md`. Regras de exibição (5 resultados, cada um em uma mensagem, links de contato) em `prd.md` (seção "Exibição do resultado"). Reutilizar Tarefas 3, 4 e 6.

## Critérios de Sucesso

- Retorna até 5 resultados mais similares, cada um com os links de contato disponíveis.
- Resposta gerada respeita o `input_guide` e considera o histórico.
- Histórico persistido com TTL de 30 min após a interação.

## Testes da Tarefa

- [ ] Testes de unidade (orquestração com dependências mockadas: com e sem histórico; formatação dos resultados/links)
- [ ] Testes de integração (busca por similaridade + geração de resposta com serviços de teste isolados)
- [ ] Testes E2E (se aplicável — coberto via endpoints na Tarefa 10)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/search_answer.py` (ou nome equivalente)
- `app/infrastructure/*` (serviços/repos reutilizados)
- `tests/unit/application/`, `tests/integration/`
