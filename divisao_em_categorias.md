# Divisão da base de conhecimento em categorias


## Contexto
Atualmente, a base de conhecimento é tratada como um único conjunto de informações, o que pode dificultar a busca e a organização dos dados e demora na leitura das informações.


## Plano
Para melhorar a eficiência e a relevância das respostas fornecidas pelo sistema, é necessário implementar uma funcionalidade que divida a base de conhecimento em categorias distintas.
Quando um registro de conhecimento for adicionado, ele deve ser classificado em uma das categorias predefinidas,
cadastrar no arquivo correto no bucket referente a essa categoria.
Quando uma pergunta for feita, o sistema deve identificar a categoria mais relevante para a pergunta e buscar as informações apenas nessa categoria, melhorando a precisão e a velocidade da resposta.


## Tarefas

### Categorias predefinidas
As categorias predefinidas são:
```text
ALIMENTAÇÃO
SAÚDE
BELEZA
CONSTRUÇÃO
AUTOMOTIVO
TECNOLOGIA
COMÉRCIO
EDUCAÇÃO
SERVIÇOS PROFISSIONAIS
TRANSPORTE
CASA E MANUTENÇÃO
ANIMAIS
EVENTOS
TURISMO
ENTRETENIMENTO
MODA
FINANCEIRO
AGROPECUÁRIA
RELIGIÃO
SERVIÇOS PÚBLICOS
```

Elas devem permanecer no redis para que possam ser utilizadas em outros pontos do sistema, como na classificação de novos serviços.


### Cadastro de novos serviços
- Quando novos serviços forem cadastrados, eles devem ser classificados em uma das categorias predefinidas.
Altere o prompt de moderação da LLM e o método `moderate` no `@app/infrastructure/openai/service.py` para que a LLM classifique o serviço em uma das categorias predefinidas (consulte o redis e informe as categorias).
- Se não existir uma categoria adequada, a LLM deve retornar uma outra categoria de sugestão.
A categoria deve vir num outro objeto chamado 'categoria' no json de resposta da LLM e depois inserida na lista de categorias no redis.
- Definida a categoria, o serviço deve ser gravado no bucket correto referente a essa categoria.
Atualmente o nome do arquivo no bucket é 'client_services.jsonl'. Ele deve ser alterado para 'client_services_{categoria}.jsonl', onde {categoria} é a categoria definida pela LLM.
- Definida a categoria, o serviço deve guardar a base de conhecimento no `pinecone` com novo key referente a essa categoria. Atualmente ele grava somente _id, text e user_code.


### Busca de informações
- Quando uma pergunta for feita, o sistema deve identificar a categoria mais relevante para a pergunta e
- Antes de enviar a consulta para o `pinecone` no método `_run_pipeline` em `@app/application/search/service.py`,
o sistema deve enviar uma nova consulta para a LLM para identificar a categoria mais relevante para a pergunta dentre as categorias predefinidas. (consulte o redis)
- Identicada a categoria, o sistema deve buscar as informações no `pinecone` somente na categoria identificada, buscando no key referente a essa categoria.
