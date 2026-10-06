# Tarefa 4.0: Serviço de Processamento de Texto

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar o serviço que prepara o texto do cliente antes da geração de embeddings: normalização
(remover linhas em branco) e divisão em chunks usando o `RecursiveCharacterTextSplitter` do
LangChain. Depende da Tarefa 2.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/instructions/gerar_chunks.md`
- `.agents/code_patterns/python-conventions.md` (constantes para valores mágicos)
- `.agents/code_patterns/architecture.md`
</skills>

<requirements>
- Normalização do texto de entrada: remover linhas em branco (e ruído conforme PRD).
- Geração de chunks com `RecursiveCharacterTextSplitter` (parâmetros via constantes/config).
- Função tipada: entrada `str` → `list[str]`.
- Separadores e tamanhos conforme instrução `gerar_chunks.md`.
</requirements>

## Subtarefas

- [ ] 4.1 Função de normalização do texto.
- [ ] 4.2 Função de geração de chunks (LangChain).
- [ ] 4.3 Testes de unidade (normalização + chunking determinístico).
- [ ] 4.4 Testes de integração (texto realista de cadastro → chunks).

## Detalhes de Implementação

Ver `tasks/techspec.md` §1.2, §1.3 e `.agents/instructions/gerar_chunks.md`
(`chunk_size`, `chunk_overlap`, `separators`). Adicionar o tipo de retorno indicado nos exemplos.

## Critérios de Sucesso

- Linhas em branco removidas; nenhum chunk vazio.
- Chunking determinístico para a mesma entrada.
- Linter e type checker passam.

## Testes da Tarefa

- [ ] Testes de unidade
- [ ] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/application/text_processing/` (novo)
- `requirements.txt` (adicionar `langchain` / `langchain-text-splitters`)
- `tests/unit/text_processing/`
