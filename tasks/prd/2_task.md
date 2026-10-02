# Tarefa 2.0: Domínio e modelos tipados

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Definir as entidades de domínio e os schemas (Pydantic) que representam os conceitos do negócio: empresa/negócio do cliente, categoria, item da base de conhecimento (knowledge_base) e mensagem/histórico do usuário. Essas estruturas serão reutilizadas por persistência, casos de uso e API.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/python-conventions.md` (tipagem obrigatória, uso de modelos/objetos).
</skills>

<requirements>
- Entidades de domínio puras, sem dependência de FastAPI, SQLAlchemy ou clientes externos (ver `architecture.md`).
- Schemas Pydantic de entrada/saída para a camada de API.
- Tipagem explícita em todos os campos (sem tipos implícitos).
- Representar: Empresa/Negócio (dados de cadastro), Categoria, KnowledgeBase (`id`, `content`, `embedding`, `langchain_metadata`), Mensagem e Histórico de conversa.
</requirements>

## Subtarefas

- [x] 2.1 Definir entidades de domínio (Empresa/Negócio, Categoria, KnowledgeBase, Mensagem/Histórico).
- [x] 2.2 Definir schemas Pydantic de requisição/resposta da API (cadastro de empresa e mensagem de usuário).
- [x] 2.3 Definir o schema do resultado de busca (inclui campos de contato: e-mail, telefone, WhatsApp).

## Detalhes de Implementação

Campos da `knowledge_base` conforme `techspec.md` (linha da tabela: `id`, `content`, `embedding`, `langchain_metadata`). Requisitos de exibição do resultado (links de e-mail/telefone/WhatsApp) em `prd.md` (seção "Exibição do resultado"). Separação domínio x infraestrutura em `.agents/code_patterns/architecture.md`.

## Critérios de Sucesso

- Entidades de domínio não importam frameworks de infraestrutura.
- Schemas validam entrada/saída corretamente.
- Modelos reutilizáveis pelas demais camadas.

## Testes da Tarefa

- [x] Testes de unidade (validação dos schemas: campos obrigatórios, tipos, limites)
- [ ] Testes de integração (se aplicável — serialização/desserialização nas rotas será coberta na Tarefa 10)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/domain/` (entidades)
- `app/api/schemas.py`
- `tests/unit/domain/`
