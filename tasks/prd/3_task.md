# Tarefa 3.0: Persistência PostgreSQL (categories, knowledge_base, pgvector)

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar a camada de persistência assíncrona em PostgreSQL: conexão/pool, as tabelas `categories` e `knowledge_base` (com suporte a vetores via pgvector) e os repositories que abstraem o acesso a dados. Inclui a consulta de similaridade usada na busca.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/architecture.md` (padrão Repository) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Conexão assíncrona com PostgreSQL, host/senha vindos de configuração/env (`arquivo_configuracoes.md`).
- Tabela `categories` com coluna `name` (consulta `select name from categories`).
- Tabela `knowledge_base` com colunas `id`, `content`, `embedding`, `langchain_metadata` e suporte a vetores (pgvector).
- Repository de categorias: listar categorias e criar nova categoria.
- Repository da knowledge_base: inserir item e consultar por similaridade (top N).
- Nenhuma credencial hardcoded.
</requirements>

## Subtarefas

- [ ] 3.1 Implementar conexão/pool assíncrono com PostgreSQL a partir da configuração.
- [ ] 3.2 Criar schema/migração das tabelas `categories` e `knowledge_base` (habilitar pgvector).
- [ ] 3.3 Implementar `CategoryRepository` (listar nomes, criar categoria).
- [ ] 3.4 Implementar `KnowledgeBaseRepository` (inserir item; consultar top 5 por similaridade).

## Detalhes de Implementação

Estrutura das tabelas e consultas em `techspec.md` (`categories`, `knowledge_base`). Padrão de repositories e injeção em `.agents/code_patterns/architecture.md`. A consulta de similaridade (top 5) alimenta o caso de uso de busca (Tarefa 9).

## Critérios de Sucesso

- Conexão assíncrona estabelecida a partir da configuração/env.
- Tabelas criadas com as colunas especificadas e índice vetorial.
- Repositories executam leitura/escrita e consulta de similaridade corretamente.

## Testes da Tarefa

- [ ] Testes de unidade (lógica dos repositories com conexão mockada/fake)
- [ ] Testes de integração (contra PostgreSQL de teste isolado: inserir e consultar similaridade)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/database/`
- `app/infrastructure/repositories/`
- `tests/unit/repositories/`, `tests/integration/database/`
