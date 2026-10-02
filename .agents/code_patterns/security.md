# Python Security Guidelines

## Secrets

Never hardcode:

* passwords,
* API keys,
* access tokens,
* private keys,
* database credentials.

Bad:

```python
API_KEY = "sk-secret-key"
```

Use environment variables or a secrets manager.

## Sensitive Data

Never log:

* passwords,
* authentication tokens,
* API keys,
* credit card information,
* private keys,
* sensitive personal information.

## Input Validation

Treat external input as untrusted.

Validate:

* type,
* format,
* length,
* allowed values,
* size.

## SQL

Never build SQL queries by concatenating user input.

Bad:

```python
query = f"SELECT * FROM users WHERE id = {user_id}"
```

Use parameterized queries or the ORM's safe query mechanisms.

## Dependencies

Keep dependencies updated.

Regularly check for known vulnerabilities.

Do not install packages without verifying their source and purpose.

## Authentication

Never implement custom cryptography unless there is a strong and well-understood requirement.

Prefer established libraries and protocols.

## Authorization

Authentication answers:

> Who are you?

Authorization answers:

> What are you allowed to do?

Always enforce authorization on the server side.

Do not trust authorization information supplied only by the client.

## File Handling

Treat uploaded files as untrusted.

Validate:

* file type,
* file size,
* file name,
* storage location.

Avoid using user-provided paths directly.

## External APIs

Protect credentials and validate responses from external services.

Use timeouts.

Avoid making external requests without a defined timeout.

Example:

```python
response = client.get(
    url,
    timeout=10,
)
```

## Error Messages

Do not expose:

* stack traces,
* database credentials,
* internal infrastructure,
* filesystem paths,
* secrets.

Return safe messages to external clients while logging diagnostic information internally.
