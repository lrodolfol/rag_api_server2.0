# Especificação técnica

## Arquitetura do sistema

Cliente -> envia informações para API
    API -> pega as informações e consulta openAI para categorizar a empresa do cliente
            -> as categorias estão no banco de dados na tabela `categories`. `select name from categories`
                -> se não existir uma boa categoria para o cliente, deve-se criar uma nova categoria no banco de dados
                -> se for infomação agressiva, pare a aplicação
    API -> normaliza as informações removendo linhas em branco
    API -> gera chunks das informações
    API -> usa os chunks para gerar embeddings consultando a openAI
    API -> atualiza o bucket com nova informação vinda do cliente
    API -> buscar o arquivo no bucket grava os embeddings e as informações do cliente no postgresql na tabela `knowledge_base` que tem as colunas: `id`, `content`, `embedding` e `langchain_metadata`
Usuário -> envia mensagem para API
    API -> busca historico de mensagem do usuário (se existir)
    API -> gera embeddings da mensagem do cliente
    API -> consulta a base de dados para buscar dados com maiores similaridades
    API -> pega o retorno das similaridades e faz pergunta para a openAI
    API -> pega o retorno da openAI para devolver a resposta para o usuário

## Fluxo mermaid
- ./fluxo_mermaid.md