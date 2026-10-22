## Arquivo de configurações

Sempre utilize arquivo de configuração para dados dinamicos

## PROD FILE
```json
{
  "open_ai": {
    "api_key": "get from environment",
    "model_embeddings": "text-embedding-3-small",
    "model_chat": "gpt-3.5-turbo",
    "input_guide": "<role>Você é um assistente de IA que responde usando exclusivamente a base de conhecimento fornecida.</role> <constraints>- Antes de qualquer coisa, se a mensagem do usuário for apenas um cumprimento ou agradecimento (ex: 'ola', 'oi', 'bom dia', 'obrigado'), responda apenas com outro cumprimento. Ignore as outras regras nesses casos.- Se a mensagem contiver palavrões, ofensas ou conteúdo inadequado, não responda.- Para qualquer pergunta ou solicitação, responda somente com base na base de conhecimento fornecida.- Caso a pergunta não esteja na base, responda com: 'response_answer'.- Nunca mencione a base de conhecimento ao responder.- Se houver várias respostas possíveis na base, inclua todas.- Considere sempre o histórico da conversa ao responder. - Responda exclusivamente no idioma da pergunta do usuário.- Mantenha suas respostas concisas e diretas. - Nunca peça informações pessoais ao usuário. - Ao ler a base de conhecimento, corrija erros de ortografia ou gramática, se houver. <critical>**NUNCA, JAMAIS RESPONDA INFORMAÇÕES PESSOAIS, SENSÍVEIS OU CONFIDENCIAIS.**</critical></constraints>",
    "pattern_response": "Não consegui encontrar uma resposta para sua pergunta com base na minha base de conhecimento"
  },
  "pinecone": {
    "api_key": "get from environment",
    "index_name": "acha-local-services-prod",
    "region": "us-east-1",
    "environment": "production",
    "metric": "cosine",
    "vector_type": "dense",
    "dimension": 1536
  },  
  "redis": {
    "host": "localhost",
    "port": "6379",
    "db": 0,
    "password": "get from environment"
  },
  "company": {
    "name": "TI NOS NEGOCIOS",
    "email": "tinosnegocios1@gmail.com",
    "ceo": {
      "name": "Rodolfo de Jesus Silva,",
      "person_email": "rodolfo0ti@gmail.com",
      "professional_emai": "ceo@tinosnegocios.com.br"
    }
  },
  "bucket": {
    "name": "tnn-rag",
    "bucket_name": "acha-local",
    "host": null,
    "access_key": "get from environment",
    "secret_key": "get from environment",
    "region": "us-east-1"
  }
}
```

## DEV file
```json
{
  "open_ai": {
    "api_key": "get from environment",
    "model_embeddings": "text-embedding-3-small",
    "model_chat": "gpt-3.5-turbo",
    "input_guide": "<role>Você é um assistente de IA que responde usando exclusivamente a base de conhecimento fornecida.</role> <constraints>- Antes de qualquer coisa, se a mensagem do usuário for apenas um cumprimento ou agradecimento (ex: 'ola', 'oi', 'bom dia', 'obrigado'), responda apenas com outro cumprimento. Ignore as outras regras nesses casos.- Se a mensagem contiver palavrões, ofensas ou conteúdo inadequado, não responda.- Para qualquer pergunta ou solicitação, responda somente com base na base de conhecimento fornecida.- Caso a pergunta não esteja na base, responda com: 'response_answer'.- Nunca mencione a base de conhecimento ao responder.- Se houver várias respostas possíveis na base, inclua todas.- Considere sempre o histórico da conversa ao responder. - Responda exclusivamente no idioma da pergunta do usuário.- Mantenha suas respostas concisas e diretas. - Nunca peça informações pessoais ao usuário. - Ao ler a base de conhecimento, corrija erros de ortografia ou gramática, se houver. <critical>**NUNCA, JAMAIS RESPONDA INFORMAÇÕES PESSOAIS, SENSÍVEIS OU CONFIDENCIAIS.**</critical></constraints>",
    "pattern_response": "Não consegui encontrar uma resposta para sua pergunta com base na minha base de conhecimento"
  },
  "pinecone": {
    "api_key": "get from environment",
    "index_name": "acha-local-services-dev",
    "region": "us-east-1",
    "environment": "development",
    "metric": "cosine",
    "vector_type": "dense",
    "dimension": 1536
  },  
  "redis": {
    "host": "localhost",
    "port": "6379",
    "db": 0,
    "password": "get from environment"
  },
  "company": {
    "name": "TI NOS NEGOCIOS",
    "email": "tinosnegocios1@gmail.com",
    "ceo": {
      "name": "Rodolfo de Jesus Silva,",
      "person_email": "rodolfo0ti@gmail.com",
      "professional_emai": "ceo@tinosnegocios.com.br"
    }
  },
  "bucket": {
    "name": "tnn-rag",
    "bucket_name": "acha-local",
    "access_key": "get from environment",
    "secret_key": "get from environment",
    "region": "us-east-1"
  }
}
```

## Substituição de `pattern_response` no `input_guide`

O campo `input_guide` deve conter o placeholder literal `'response_answer'` na posição onde a mensagem de fallback deve aparecer.

O campo `pattern_response` contém o texto real da resposta de fallback.

Na carga da configuração, `OpenAIConfig` substitui automaticamente `'response_answer'` pelo valor de `pattern_response` via `model_validator`. O `OpenAIService` já recebe o `input_guide` final, sem placeholder.

**Regra:** sempre mantenha `'response_answer'` como placeholder no `input_guide` do arquivo de configuração. Altere somente `pattern_response` para personalizar a mensagem de fallback por ambiente.