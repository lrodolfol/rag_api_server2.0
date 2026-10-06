# Tarefa 1.0: Fundação de Configuração

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar a base de configuração tipada da aplicação. Carregar valores dinâmicos de um arquivo
`env.json` (variantes dev/prod) e obter todos os dados sensíveis (API keys, senhas, secret
keys) exclusivamente de variáveis de ambiente. Nenhuma outra tarefa deve ler configuração de
outra forma — todas dependem desta.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/architecture.md` (seção Configuration — objeto de config tipado)
- `.agents/code_patterns/security.md` (segredos nunca hardcoded)
- `.agents/code_patterns/python-conventions.md`
- `.agents/instructions/arquivo_configuracoes.md` (estrutura do arquivo dev/prod)
</skills>

<requirements>
- Objeto de configuração tipado (pydantic) com seções: `open_ai`, `pinecone`, `redis`, `company`, `bucket`.
- Valores dinâmicos vêm de `env.json`; segredos (`api_key`, `password`, `access_key`, `secret_key`) vêm de variáveis de ambiente — NUNCA do arquivo.
- Seleção de ambiente (dev/prod) via variável de ambiente.
- Fornecer um `env.example.json` versionado (sem segredos reais) para referência.
- Carregamento único/reutilizável (sem reler o arquivo a cada acesso).
- Nenhum dado sensível hardcoded ou logado.
</requirements>

## Subtarefas

- [x] 1.1 Definir os modelos tipados de configuração (uma classe por seção + raiz).
- [x] 1.2 Implementar o carregador que lê `env.json` e injeta segredos de variáveis de ambiente.
- [x] 1.3 Criar `env.example.json` e documentar as variáveis de ambiente necessárias.
- [x] 1.4 Testes de unidade do carregamento e da resolução de segredos.
- [x] 1.5 Testes de integração (arquivo real + env vars de teste).

## Detalhes de Implementação

Ver estrutura dos arquivos dev/prod em `tasks/techspec.md` e `.agents/instructions/arquivo_configuracoes.md`.
Campos marcados como `"get from environment"` devem ser substituídos por variáveis de ambiente.

## Critérios de Sucesso

- Config carrega corretamente para dev e prod.
- Segredos resolvidos a partir de variáveis de ambiente; ausência de segredo falha de forma clara.
- `grep` por chaves/segredos no código não retorna nada hardcoded.
- Linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [ ] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/config/` (novo módulo de configuração)
- `env.example.json` (novo)
- `requirements.txt` (adicionar `pydantic-settings` se usado)
- `tests/unit/config/`, `tests/integration/config/`
