# Tarefa 7.0: Processamento de texto (normalização e geração de chunks)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o processamento de texto do fluxo de cadastro: normalização das informações do cliente (remoção de linhas em branco e de erros) e geração de chunks a partir do texto normalizado, usados posteriormente para gerar embeddings.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/python-conventions.md`.
</skills>

<requirements>
- Normalizar informações removendo linhas em branco (e erros ortográficos conforme PRD).
- Gerar chunks com `RecursiveCharacterTextSplitter` conforme `.agents/instructions/gerar_chunks.md`.
- Funções puras e tipadas, sem dependência de infraestrutura.
</requirements>

## Subtarefas

- [ ] 7.1 Implementar normalização do texto (remover linhas em branco / limpeza conforme PRD).
- [ ] 7.2 Implementar geração de chunks (`RecursiveCharacterTextSplitter`, parâmetros de `gerar_chunks.md`).

## Detalhes de Implementação

Passos de normalização e geração de chunks em `techspec.md` e `fluxo_mermaid.md`. Implementação de referência dos chunks em `.agents/instructions/gerar_chunks.md` (chunk_size, overlap e separadores). Regras de normalização (linhas em branco, ortografia) em `prd.md`.

## Critérios de Sucesso

- Texto com linhas em branco é normalizado corretamente.
- Geração de chunks respeita tamanho/overlap definidos.
- Funções determinísticas e tipadas.

## Testes da Tarefa

- [ ] Testes de unidade (normalização e divisão em chunks com entradas variadas)
- [ ] Testes de integração (se aplicável — integração coberta na Tarefa 8)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/` ou `app/domain/services/` (processamento de texto)
- `tests/unit/`
