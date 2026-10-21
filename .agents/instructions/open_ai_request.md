## Como enviar perguntas a openAI via API
```python
client_payload = [
    {"role": "system", "content": self.input_guide},
    *historic,
    {"role": "user", "content": f"Pergunta: {payload_open_ia.question}"},
    {"role": "system", "content": f"Trechos: {phrases}"}
]
```

- `self.input_guide`: carregado do arquivo de configuração. O placeholder `'response_answer'` é substituído automaticamente pelo valor de `pattern_response` no momento em que `OpenAIConfig` é construído (ver `app/infrastructure/config/models.py`). Consulte `./arquivo_configuracoes.md`.
- `historic`: todo o histórico de conversa do usuário até o momento
- `payload_open_ia.question`: a pergunta do usuário
- `phrases`: listas de similaridade vindas do banco de dados vetorial

## Substituição do `pattern_response` no `input_guide`

O campo `input_guide` em `env.json` usa o placeholder `'response_answer'` para indicar onde a mensagem de fallback deve aparecer.

O campo `pattern_response` em `env.json` contém o texto real que será exibido ao usuário quando não houver resposta na base de conhecimento.

A substituição ocorre em `OpenAIConfig._substitute_pattern_response` (validador Pydantic `model_validator`) e acontece **uma única vez**, na carga da configuração. O `OpenAIService` recebe o `input_guide` já com o texto final, sem necessidade de qualquer lógica adicional.