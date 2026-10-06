# Configuration

Typed, cached application configuration.

- **Dynamic (non-sensitive) values** come from `env.json` at the project root.
  The file holds a `dev` and a `prod` variant; use `env.example.json` as the
  template (copy it to `env.json`).
- **Secrets** come exclusively from environment variables — never from the file.

## Usage

```python
from app.infrastructure.config import get_config

config = get_config()  # cached: the file is read and validated only once
config.pinecone.index_name
config.open_ai.api_key.get_secret_value()
```

## Environment variables

| Variable            | Purpose                                             | Required |
| ------------------- | --------------------------------------------------- | -------- |
| `ENVIRONMENT`       | Selects the variant in `env.json` (`dev` / `prod`). | No (defaults to `dev`) |
| `CONFIG_FILE`       | Absolute path override for the config file.         | No (defaults to `<project>/env.json`) |
| `OPEN_IA_API_KEY`   | OpenAI API key → `open_ai.api_key`.                 | Yes |
| `PINECONE_API_KEY`  | Pinecone API key → `pinecone.api_key`.              | Yes |
| `REDIS_PASSWORD`    | Redis password → `redis.password`.                  | Yes |
| `CLOUD_ACCESS_KEY`  | Bucket access key → `bucket.access_key`.            | Yes |
| `CLOUD_SECRET_KEY`  | Bucket secret key → `bucket.secret_key`.            | Yes |

A missing required secret raises `ConfigError` at load time.
Secrets are stored as `pydantic.SecretStr` and are masked in logs and `repr`.
