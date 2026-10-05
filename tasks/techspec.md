# Especificação técnica

## Arquitetura do sistema

1- Cliente -> envia informações para API
    1.1 - API -> pega as informações e consulta LLM(openAI) para filtrar, e se for infomação agressiva, pare a aplicação
    1.2 - API -> normaliza as informações removendo linhas em branco
    1.3 - API -> gera chunks das informações usando o langchain
    1.4 - API -> usa os chunks para gerar embeddings consultando a openAI
    1.5 - API -> atualiza o bucket S3 com nova informação vinda do cliente
    1.6 - API -> grava os embeddings e as informações do cliente no pinecone com informações: `id`, `embedding`, `content`
2- Usuário -> envia mensagem pela API de integração com whatsapp
    API -> 2.1 - busca historico de mensagem do usuário (se existir)
    API -> 2.2 - gera embeddings da mensagem do cliente
    API -> 2.3 - consulta a base de dados para buscar dados com maiores similaridades
    API -> 2.4 - pega o retorno das similaridades e faz pergunta para a openAI
    API -> 2.5 - pega o retorno da openAI para devolver a resposta para o usuário
3- Usuário -> envia mensagem pela API de chat online
    API -> 3.1 - verifique a quantidade de mensagens desse chat, bloqueie caso a quantidade de mensagens seja maior que 3
    API -> 3.2 - busca historico de mensagem do usuário (se existir)
    API -> 3.3 - gera embeddings da mensagem do cliente
    API -> 3.4 - consulta a base de dados para buscar dados com maiores similaridades
    API -> 3.5 - pega o retorno das similaridades e faz pergunta para a openAI
    API -> 3.6 - pega o retorno da openAI para devolver a resposta para o usuário    

## Formas de código:

1. Deverá vir o código do cliente e os dados da empresa.
Exemplo:
```json
{
    "user_code": "1234567890",
    "request": {
        "name": "nome da empresa",
        "descricao": "descricao da empresa",
        "email": "email da empresa",
        "address": "endereco da empresa",
        "telephone": "telefone de contato",
        "detalhes": "Horário de funcionamento: Seg a Sex: 08h ~ 19h \n
        Formas de pagamento: dinheiro, pix e cartão de crédito \n
        Estacionamento próprio \n
        Site: www.exemplo.com.br \n
        Categoria: gratuito/economico/moderado/premium \n
        Delivery: Sim \n
        Entrega gratuida em domicilio \n
        "

    }
}
```

1.1. Exemplo de questionamento para OPENAI:
prompt: Você é um assistente especialista analise de informações enviadas pelo cliente. 
Dado as informações abaixo que o cliente enviou, verifique se há qualquer tipo de xingamentos ou conteúdos inapropriados e confirme, caso existir.
Informaçãos do cliente:
{dados-do-cliente}

Responda de forma objetiva e direta em forma de json. Exemplos:
a -
```json
{
    "insult": true,
    "insult": "texto com insulto ou palavrões"
}
```
b -
```json
{
    "insult": false,
    "insult": ""
}
```

1.3. Exemplo para gerar chunks com logchain
```python
def generate_chunks(texto: str): #instrução para LLM: colocar tipo de retorno
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,       # tamanho do chunk (em caracteres)
        chunk_overlap=50,     # sobreposição entre chunks
        separators=["\n\n", "\n", ".", " ", ""]  # tentará quebrar nessa ordem
    )

    chunks = splitter.split_text(texto)

    return chunks
```

1.4. Exmplo para gerar os vetores
```python
    def generate_embeddings_from_chunks(self, lista_chunks: list[str]) -> list[dict]: #instrução para LLM: Validar se o tipo de retorno está correto
        embeddings: list = []

        for chunk in lista_chunks:
            vector: list[float] = self.generate_vector_from_chunks(chunk)
            embeddings.append({"text": chunk, "vector": vector})

        return embeddings


    def generate_vector_from_chunks(self, chunk) -> list[float]:
        response: CreateEmbeddingResponse = open_ai_client.embeddings.create(
            input=chunk,
            model=self.model_embeddings #instrução para LLM: ´model_embeddings´ é uma parametro de configuração para text-embedding-ada-002
        )

        vector: list[float] = response.data[0].embedding

        return vector
```        

1.5. Nome do bucket: 'client_services'
formato do arquivo: jsonl

1.6.  Já que será necessário atualizar uma informação de usuario, é necessário criar um indice caso nao exista, deletar o vetor pelo código do cliente 
e cadastrar as novas informações do cliente para atualização.

Exemplos: 
deletar indice:
```python
        try:
            self.create_index_if_not_exists()
            index = self.pinecone.Index(self.index_name)
            index.delete(filter={"user_code": user_code})
            self.logger.info(f"Vectors deleted for user {user_code}.")
        except Exception as e:
            self.logger.error(f"Error deleting Pinecone vectors for user {user_code}: {e}")
            return
```            

criar indice(se nao existir) - (todos parametros vem do arquivo de configurações {env.json})
```python
    def create_index_if_not_exists(self) -> None:
        if not self.pinecone.has_index(self.index_name):
            try:
                self.pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    vector_type=self.vector_type,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.region
                    ),
                    deletion_protection="disabled",
                    tags={
                        "environment": self.environment,
                    }
                )
                self.logger.info(f"Index '{self.index_name}' created successfully.")
            except Exception as e:
                self.logger.error(f"Error creating index: {e}")
```                

gravar dados no pinecone com os vetores ja preenchidos:
```python
            index = self.pinecone.Index(self.index_name)

            vector_insert = [
                (
                    f"{company.replace(' ','')}-{user_code}-{i}",
                    item["vector"],
                    {"text": item["text"], "user_code": user_code, ""}
                )
                for i, item in enumerate(embeddings)
            ]

            if vector_insert:
                index.upsert(vector_insert)
                self.logger.info(f"Data saved successfully for user {user_code}.")
```                


2.
Exemplo de mensagem pela API de chat online:
```json
{
  "number": "5535999999999",
  "text": "Olá! Esta é uma mensagem de teste enviada pela Evolution API.",
  "delay": 1200,
  "linkPreview": false
}
```

2.1 o historico de mensagens ficará no redis com a chave 'users_histotic_whatsapp'

2.2 exemplo para gerar os vetores:
```python
    def generate_embeddings_question(self, question: str) ->list[float]:
        if self.has_invalid_properties():
            return[]

        response: CreateEmbeddingResponse = self.client.embeddings.create(
            input=question,
            model=self.model_embeddings
        )

        return response.data[0].embedding
```

2.3 exemplo para consultar o pinecone:
```python
    def get(self, embedding, top_k=5):
        if self.has_invalid_properties():
            return None

        try:
            self.create_index_if_not_exists()
            index = self.pinecone.Index(self.index_name)

            query_response = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )

            return query_response

        except Exception as e:
            self.logger.error(f"Error retrieving data from Pinecone: {e}")
            return []
```            

2.4 exemplo para pergunta com OPENAI:
os parametros devem vir do arquivo de configurações {env.json}
```python
    def make_question(self, payload_open_ia: PayloadQuestionOpenIA, phrases: list) -> str:
        if self.has_invalid_properties() or payload_open_ia.is_invalid():
            return ""

        historic = model_historic(payload_open_ia)

        client_payload = [
                {"role": "system", "content": self.input_guide},
                *historic,
                {"role": "user", "content": f"Pergunta: {payload_open_ia.question}"},
                {"role": "system", "content": f"Trechos: {phrases}"}
            ]
        client_response = self.client.responses.create(
            model=self.model_chat,
            input=client_payload
        )

        if not client_response:
            raise OpenIaException("No choices returned from OpenAI API")

        return client_response.output_text

    def model_historic(payload_openIA: PayloadQuestionOpenIA):
        historic = []

        if payload_openIA.chat_historic is None or len(payload_openIA.chat_historic) == 0:
            return historic

        for message in payload_openIA.chat_historic:
            if message.is_user:
                historic.append({"role": "user", "content": message.text})
            else:
                historic.append({"role": "assistant", "content": message.text})

        return historic
```        

2.5 use o padrão de resposta de API conforme `@.agents\code_patterns\api.md`



3.
Exemplo de mensagem pela API de chat online:
```json
{
  "message": "mensagem do chat online",
  "user_code": "4567895465",
  "user_ip": "200.148.12.188"
}
```

3.1 você pode bloquear o usuario pelo IP do usuário em memória com TTL de 5 horas
se o usuário atingir o limite, informe para ele com padrao de API conforme `@.agents\code_patterns\api.md`

3.2 o historico de mensagens ficará no redis com a chave 'users_histotic_online'

3.3 exemplo para gerar os vetores:
```python
    def generate_embeddings_question(self, question: str) ->list[float]:
        if self.has_invalid_properties():
            return[]

        response: CreateEmbeddingResponse = self.client.embeddings.create(
            input=question,
            model=self.model_embeddings
        )

        return response.data[0].embedding
```

3.4 exemplo para consultar o pinecone:
```python
    def get(self, embedding, top_k=5):
        if self.has_invalid_properties():
            return None

        try:
            self.create_index_if_not_exists()
            index = self.pinecone.Index(self.index_name)

            query_response = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )

            return query_response

        except Exception as e:
            self.logger.error(f"Error retrieving data from Pinecone: {e}")
            return []
```            

3.5 exemplo para pergunta com OPENAI:
os parametros devem vir do arquivo de configurações {env.json}
```python
    def make_question(self, payload_open_ia: PayloadQuestionOpenIA, phrases: list) -> str:
        if self.has_invalid_properties() or payload_open_ia.is_invalid():
            return ""

        historic = model_historic(payload_open_ia)

        client_payload = [
                {"role": "system", "content": self.input_guide},
                *historic,
                {"role": "user", "content": f"Pergunta: {payload_open_ia.question}"},
                {"role": "system", "content": f"Trechos: {phrases}"}
            ]
        client_response = self.client.responses.create(
            model=self.model_chat,
            input=client_payload
        )

        if not client_response:
            raise OpenIaException("No choices returned from OpenAI API")

        return client_response.output_text

    def model_historic(payload_openIA: PayloadQuestionOpenIA):
        historic = []

        if payload_openIA.chat_historic is None or len(payload_openIA.chat_historic) == 0:
            return historic

        for message in payload_openIA.chat_historic:
            if message.is_user:
                historic.append({"role": "user", "content": message.text})
            else:
                historic.append({"role": "assistant", "content": message.text})

        return historic
```        

3.6 use o padrão de resposta de API conforme `@.agents\code_patterns\api.md`


**OS CÓDIGOS ACIMA SÃO EXEMPLOS DE CÓDIGO, MELHORE OU APERFEIÇOE ELES, SE NECESSÁRIO**
- verifique os padrões dentro de `@.agents\code_patterns` e `@.agents\instructions`
- mantenha o código organizado e claro. Livre de complexidade absurdas
- mantenha o código em ingles