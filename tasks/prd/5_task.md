# Tarefa 5.0: Armazenamento em bucket

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Implementar o serviço de armazenamento em bucket usado no fluxo de cadastro: atualizar o bucket com a nova informação vinda do cliente e buscar o arquivo para posterior gravação na `knowledge_base`. O bucket é específico para categorização.

<skills>
### Conformidade com Skills Padrões

Nenhuma skill de projeto em `@.claude/skills` se aplica. Seguir `.agents/code_patterns/security.md` (access/secret key via env) e `.agents/code_patterns/error-handling.md`.
</skills>

<requirements>
- Configuração do bucket (nome, host, região) via arquivo de configuração; `access_key`/`secret_key` via variáveis de ambiente (`arquivo_configuracoes.md`).
- Operações assíncronas de escrita (atualizar/subir arquivo) e leitura (buscar arquivo).
- Nenhuma credencial hardcoded.
</requirements>

## Subtarefas

- [ ] 5.1 Implementar cliente/serviço de bucket configurável (credenciais via env).
- [ ] 5.2 Implementar atualização/upload de arquivo de categorização no bucket.
- [ ] 5.3 Implementar busca/download do arquivo do bucket.

## Detalhes de Implementação

Passos de "atualiza o bucket" e "busca o arquivo no bucket" em `techspec.md` e `fluxo_mermaid.md`. Parâmetros do bucket em `.agents/instructions/arquivo_configuracoes.md` (seção `bucket`).

## Critérios de Sucesso

- Arquivo é gravado/atualizado no bucket.
- Arquivo é recuperado corretamente.
- Credenciais carregadas de env, sem hardcode.

## Testes da Tarefa

- [ ] Testes de unidade (lógica do serviço com cliente de bucket mockado)
- [ ] Testes de integração (contra bucket local/fake isolado — upload e download)
- [ ] Testes E2E (se aplicável)

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/external_services/bucket/`
- `app/infrastructure/config/`
- `tests/unit/services/`, `tests/integration/`
