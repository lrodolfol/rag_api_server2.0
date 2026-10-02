# Documento de Requisitos de Produto (PRD) — Aplicação RAG

## Visao Geral

A aplicacao atual funcionará como uma API para RAG(retrieval augmented generation).

Vários clientes irão cadastrar suas respectivas empresas, comércio ou prestação de serviços com suas respectivas caracteristicas (horario de funcionamento, valores, produtos, delivery etc..)

Os usuários usarão serviços de mensagens (whatsapp) e chats online que se conectarão nessa aplicação.
Esta aplicação usará a mensagem dos usuários para encontrar as empresas ou serviços que eles procuram. 

## Objetivos

- Permitir que clientes cadastre suas empresas/serviços na aplicação.
- Persistir informações pessoas dos clientes e informação de suas empresas em forma de embedding.
- Permitir que usuários encontre empresas/serviços cadastrados utilizando RAG.
- Garantir acessibilidade (navegacao por computador ou mobile).

## Historias de Usuario

1. **Como** usuario da aplicacao, **eu quero** enviar perguntas/mensagens para a aplicação **para que** eu receba indicação de estabelecimentos baseados na minha mensagem.

## Funcionalidades Principais
- Ter um endpoint principal para mensagens vindas de integração com whatsapp
- Ter um endpoint para mensagens de chat online
- Ter um endpoint para receber as informações das empresas/negócios dos clientes e persistir em forma de embedding

### Exibicao do resultado
- Os 5 melhores resultados em similaridade devem ser exibidos para o usuário. Cada resultado em uma mensagem.
- Cada resultado deverá ter um link para e-mail, telefone e contato do whatsapp (se existir)

## Fluxo principal

### Cadastro de empresa/negócio
- Cliente informa os dados da empresa/negócio
- Aplicação normaliza os dados (remove erros ortográficos, remove linhas em branco, Ignora se tiver palavrões ou ofensas)
- Aplicação faz a categorização das informações (comida, cada, transporte, contrução, religião etc..)
- Grava as informações do cliente na base de dados normalizada (postgresql)
- Grava as informações do cliente na base de dados em forma de vetores (postgresql ou pinecone)
- Grava as informações do cliente num arquivo bucket especifico para categorização

## Busca de informações
- Cliente envia mensagem, exemplo "onde posso comer?"
- API recebe a mensagem e busca o historio de mensagem do usuario (se existir)
- Aplicação gera os embeddings da mensagem via LLM (openAI)
- Aplicação consulta a base de dados de vetores e retorna os 5 itens com maiores similaridades
- Aplicação consulta LLM (opnIA) para gerar a resposta baseada nos itens com maiores similaridades
- Envia o historio de mensagens do usuário com TTL de 30 min