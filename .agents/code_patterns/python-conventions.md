# Python Conventions

## General Principles

Follow these principles when writing Python code:

* Prefer simple and readable code over clever code.
* Follow PEP 8.
* Use descriptive names for variables, functions, classes, and modules.
* Keep functions small and focused on a single responsibility.
* Avoid unnecessary abstractions.
* Prefer explicit code over implicit behavior.
* Avoid duplicated logic.
* Do not introduce dependencies without a clear reason.

## Python Version

Use the Python version defined by the project configuration.

Check:

* `pyproject.toml`
* `.python-version`
* `requirements.txt`
* `Dockerfile`

Do not use language features that are incompatible with the project's supported Python version.

## Type Hints

Use type hints for functions, methods, and important variables.

Prefer:

```python
def calculate_total(price: float, quantity: int) -> float:
    return price * quantity
```

Instead of:

```python
def calculate_total(price, quantity):
    return price * quantity
```

Use modern Python typing when supported by the project's Python version.

Avoid using `Any` unless there is a specific reason.

## Naming

Use:

* `snake_case` for variables and functions.
* `PascalCase` for classes.
* `UPPER_CASE` for constants.
* Descriptive names instead of abbreviations.

Good:

```python
customer_repository
calculate_order_total
MAX_RETRY_ATTEMPTS
```

Avoid:

```python
cr
calc
x
tmp
```

unless the scope is extremely small and the meaning is obvious.

## Functions

Functions should have a single responsibility.

Prefer:

```python
def validate_customer(customer: Customer) -> None:
    ...

def save_customer(customer: Customer) -> None:
    ...
```

Instead of:

```python
def process_customer(customer):
    # validate
    # transform
    # save
    # send email
    # log
```

Avoid functions with excessive parameters.

When a function requires many related parameters, consider using a domain object or data class.

## Classes

Classes should represent a clear responsibility.

Avoid creating classes simply to wrap a function.

Prefer composition over inheritance unless inheritance represents a genuine "is-a" relationship.

## Imports

Organize imports in this order:

1. Standard library.
2. Third-party dependencies.
3. Local application imports.

Example:

```python
import logging
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.domain.customer import Customer
from app.repositories.customer import CustomerRepository
```

Avoid wildcard imports:

```python
from module import *
```

## Constants

Do not scatter magic values throughout the code.

Avoid:

```python
if retry_count > 3:
    ...
```

Prefer:

```python
MAX_RETRY_ATTEMPTS = 3

if retry_count > MAX_RETRY_ATTEMPTS:
    ...
```

## Comments

Write code that is self-explanatory.

Comments should explain **why**, not simply repeat **what** the code does.

Avoid:

```python
# Increment counter
counter += 1
```

Prefer:

```python
# Retry the operation because the external service may still be initializing.
retry_count += 1
```

## Docstrings

Use docstrings for public APIs, classes, and functions when their behavior is not obvious.

Example:

```python
def calculate_discount(price: float, percentage: float) -> float:
    """Calculate the discounted price."""
    return price * (1 - percentage)
```

## Logging

Use Python's `logging` module instead of `print()` for application logging.

Prefer:

```python
logger.info("Customer created", extra={"customer_id": customer_id})
```

Avoid:

```python
print(f"Customer created: {customer_id}")
```

Do not log passwords, tokens, API keys, credentials, or sensitive personal information.

## Dependencies

Before adding a dependency:

1. Check whether the standard library already provides the required functionality.
2. Check whether an existing project dependency can solve the problem.
3. Evaluate maintenance, security, and complexity.
4. Add the dependency only when justified.

## Code Quality

Before considering code complete:

* Run the formatter.
* Run the linter.
* Run type checking when configured.
* Run tests.
* Remove unused imports.
* Remove dead code.
* Remove unnecessary comments.
* Avoid TODOs unless they represent a real planned task.
