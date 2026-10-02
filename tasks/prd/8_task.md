# Tarefa 8.0: Caso de uso — Cadastro de empresa/negócio

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o caso de uso que orquestra o cadastro de uma empresa/negócio, integrando as capacidades das tarefas anteriores: categorização, parada por conteúdo agressivo, normalização, geração de chunks, geração de embeddings, atualização do bucket e gravação na `knowledge_base`.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/architecture.md` (orquestração na camada application) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Orquestrar a sequência: categorizar → (se agressivo, interromper) → criar categoria se necessário → normalizar → gerar chunks → gerar embeddings → atualizar bucket → buscar arquivo → gravar na `knowledge_base`.
- Reutilizar os serviços/repositories das Tarefas 3, 4, 5 e 7 (sem duplicar lógica).
- Parar o processamento quando a informação for agressiva/ofensiva.
- Caso de uso na camada `application`, sem acoplar à camada de API.
</requirements>

## Subtarefas

- [ ] 8.1 Implementar o caso de uso de cadastro orquestrando categorização e parada por conteúdo agressivo.
- [ ] 8.2 Encadear normalização → chunks → embeddings → atualização do bucket.
- [ ] 8.3 Gravar embeddings e informações do cliente na `knowledge_base`.

## Detalhes de Implementação

Fluxo completo de cadastro em `techspec.md` (bloco "Cliente -> envia informações") e `fluxo_mermaid.md` (nós A→L e desvio de conteúdo agressivo). Reutilizar: categorização/embeddings (Tarefa 4), bucket (Tarefa 5), chunks/normalização (Tarefa 7), repositories (Tarefa 3).

## Critérios de Sucesso

- Cadastro válido resulta em item persistido na `knowledge_base` com embedding.
- Categoria inexistente é criada antes da persistência.
- Conteúdo agressivo interrompe o fluxo sem persistir.

## Testes da Tarefa

- [ ] Testes de unidade (orquestração com dependências mockadas: caminhos feliz, nova categoria e conteúdo agressivo)
- [ ] Testes de integração (fluxo integrando repositories/serviços de teste isolados)
- [ ] Testes E2E (se aplicável — coberto via endpoint na Tarefa 10)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/register_company.py` (ou nome equivalente)
- `app/infrastructure/*` (serviços/repos reutilizados)
- `tests/unit/application/`, `tests/integration/`
