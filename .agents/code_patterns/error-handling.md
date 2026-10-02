# Error Handling Guidelines

## General Principles

Errors should be handled intentionally.

Do not use exceptions as normal control flow when a simpler approach exists.

## Specific Exceptions

Avoid catching generic exceptions unnecessarily.

Avoid:

```python
try:
    process()
except Exception:
    pass
```

Prefer:

```python
try:
    process()
except CustomerNotFoundError:
    ...
```

## Do Not Hide Errors

Never silently ignore errors.

Bad:

```python
try:
    save_customer()
except Exception:
    pass
```

If an error cannot be handled at the current level, allow it to propagate or re-raise it.

## Domain Exceptions

Use domain-specific exceptions for business errors.

Example:

```python
class CustomerNotFoundError(Exception):
    pass
```

Then:

```python
customer = repository.get_by_id(customer_id)

if customer is None:
    raise CustomerNotFoundError(customer_id)
```

## API Error Handling

Do not expose internal implementation details to API clients.

Avoid returning:

```text
Database connection failed at 10.20.30.40:5432
```

Prefer a safe response:

```json
{
  "error": "internal_server_error",
  "message": "An unexpected error occurred."
}
```

## Logging Exceptions

Log useful diagnostic information while avoiding sensitive data.

Use exception logging when appropriate:

```python
logger.exception("Failed to process customer")
```

## Validation

Validate input at the application/API boundary.

Do not rely exclusively on database constraints for user input validation.

Business validation should remain close to the business logic.

## Retry

Retries should only be used for failures that may be transient.

Examples:

* temporary network failures,
* rate limits,
* temporary service unavailability.

Do not retry permanent business errors.

Use bounded retries and appropriate backoff.
