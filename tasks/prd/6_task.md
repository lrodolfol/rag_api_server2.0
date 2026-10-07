# Tarefa 6.0: Serviço de Armazenamento em Bucket S3

<critical>Ler os arquivos de prd.md e techspec.md desta pasta, se você não ler esses arquivos sua tarefa será invalidada</critical>

## Visão Geral

Criar o serviço que persiste as informações do cliente em um bucket (S3) no formato JSONL,
como parte do fluxo de cadastro de empresa. Depende das Tarefas 1.0 e 2.0.

<skills>
### Conformidade com Skills Padrões

- `.agents/code_patterns/architecture.md` (infraestrutura separada do domínio)
- `.agents/code_patterns/security.md` (credenciais via env, timeouts)
- `.agents/code_patterns/error-handling.md`
</skills>

<requirements>
- Gravar/atualizar os dados do cliente no bucket configurado, em formato `jsonl`.
- Nome/host/credenciais do bucket vêm da config (Tarefa 1.0); segredos via variáveis de ambiente.
- Métodos assíncronos/tipados com tratamento de erro e logs sem dados sensíveis.
- Usar timeouts nas chamadas ao serviço externo.
</requirements>

## Subtarefas

- [x] 6.1 Cliente de bucket configurável a partir da config.
- [x] 6.2 Escrita/atualização do registro do cliente em JSONL.
- [x] 6.3 Testes de unidade (cliente S3 mockado, ex.: `moto`/stub).
- [x] 6.4 Testes de integração (bucket fake/local, sem serviço real).

## Detalhes de Implementação

Ver `tasks/techspec.md` §1.5 (nome do bucket e formato `jsonl`) e a seção `bucket` em
`.agents/instructions/arquivo_configuracoes.md`.

## Critérios de Sucesso

- Registro do cliente persistido em JSONL no bucket configurado.
- Nenhuma credencial hardcoded ou logada.
- Linter e type checker passam.

## Testes da Tarefa

- [x] Testes de unidade
- [x] Testes de integração
- [x] Testes E2E (se aplicável) — N/A

<critical>SEMPRE CRIE E EXECUTE OS TESTES DA TAREFA ANTES DE CONSIDERÁ-LA FINALIZADA</critical>

## Arquivos relevantes

- `app/infrastructure/storage/` (novo)
- `requirements.txt` (adicionar `boto3`)
- `tests/unit/storage/`, `tests/integration/storage/`
