## Como enviar perguntas a openAI via API
```python
client_payload = [
    {"role": "system", "content": self.input_guide},
    *historic,
    {"role": "user", "content": f"Pergunta: {payload_open_ia.question}"},
    {"role": "system", "content": f"Trechos: {phrases}"}
]
```

- self.input_guide: deverá vir do arquivo de configuração em forma JSON. consulta `./arquivo_configuracoes.md`
- historic: é todo historio de conversa do usuario até o momento
- payload_open_ia.question: é a pergunta do usuário
- phrases: são as listas de similaridade vindas do banco de dados em vetor