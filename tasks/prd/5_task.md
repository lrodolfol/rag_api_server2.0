# Tarefa 5.0: Repositório de Vetores Pinecone

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar o repositório de vetores no Pinecone: criar o índice se não existir, inserir (upsert)
vetores, deletar vetores por `user_code` (semântica de atualização) e consultar por
similaridade retornando **apenas itens com similaridade maior que 0.9**. Depende das
Tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/architecture.md` (repositório, baixo acoplamento)
- `.agents/code_patterns/error-handling.md`
- `.agents/code_patterns/python-conventions.md`
- `.agents/instructions/arquivo_configuracoes.md` (parâmetros do índice)
</skills>

<requirements>
- `create_index_if_not_exists` usando parâmetros da config (`index_name`, `dimension`, `metric`, `vector_type`, `region`, `environment`).
- Upsert de vetores com id determinístico por `user_code` e metadados (`text`, `user_code`).
- Delete por `user_code` antes do novo upsert (atualização de informações do cliente).
- Query por embedding com `top_k` e `include_metadata`, filtrando resultados com score > 0.9.
- Tipado, com tratamento de erro e logs (sem dados sensíveis).
</requirements>

## Subtarefas

- [x] 5.1 Criação de índice condicional a partir da config.
- [x] 5.2 Upsert de vetores com metadados.
- [x] 5.3 Delete por `user_code`.
- [x] 5.4 Query com corte de similaridade > 0.9.
- [x] 5.5 Testes de unidade (cliente Pinecone mockado).
- [x] 5.6 Testes de integração (fake/mock, sem serviço real).

## Detalhes de Implementação

Ver `tasks/techspec.md` §1.6 (criar índice, deletar por filtro, upsert) e §2.3/§3.4 (query).
O corte de 0.9 é requisito do PRD (seção "Exibição do resultado").

## Critérios de Sucesso

- Índice criado apenas quando ausente.
- Atualização de cliente remove vetores antigos antes de inserir novos.
- Query retorna somente itens acima do limiar de similaridade.
- Linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/pinecone/` (novo)
- `requirements.txt` (adicionar `pinecone`)
- `tests/unit/pinecone/`, `tests/integration/pinecone/`
