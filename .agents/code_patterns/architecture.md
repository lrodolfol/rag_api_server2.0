# Python Architecture Guidelines

## General Principles

The architecture should prioritize:

* Maintainability.
* Testability.
* Low coupling.
* High cohesion.
* Clear responsibilities.
* Simple dependencies.

Do not introduce architectural patterns unless they solve an actual problem.

## Separation of Concerns

Separate business logic from infrastructure concerns.

For example:

```text
src/
├── domain/
├── application/
├── infrastructure/
└── api/
```

### Domain

Contains business concepts and rules.

The domain should not depend on:

* FastAPI.
* Flask.
* SQLAlchemy.
* boto3.
* HTTP clients.
* Database implementations.

### Application

Contains use cases and application orchestration.

Example:

```text
application/
├── create_customer.py
├── update_customer.py
└── get_customer.py
```

### Infrastructure

Contains implementations that interact with external systems.

Examples:

```text
infrastructure/
├── database/
├── repositories/
├── messaging/
└── external_services/
```

### API

Contains HTTP-related concerns.

Examples:

```text
api/
├── routes/
├── schemas/
└── dependencies/
```

The API layer should not contain business logic.

## Dependency Direction

Prefer dependencies pointing toward business logic.

Example:

```text
API
 ↓
Application
 ↓
Domain

Infrastructure
 ↓
Application / Domain
```

Avoid allowing domain code to depend directly on infrastructure frameworks.

## Dependency Injection

Use dependency injection when it improves:

* testability,
* flexibility,
* separation of concerns.

Avoid creating abstractions for every class without a concrete need.

## Repositories

Repositories should abstract persistence concerns when the domain or application should not depend directly on database implementations.

Example:

```python
class CustomerRepository(Protocol):
    def get_by_id(self, customer_id: int) -> Customer | None:
        ...
```

Infrastructure provides the implementation.

## Configuration

Do not hardcode environment-specific configuration.

Prefer environment variables or a configuration system.

Example:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
```

For larger applications, use a typed configuration object.

## API Layer

API handlers should be thin.

Avoid:

```python
@router.post("/customers")
def create_customer(request):
    # validation
    # business logic
    # database access
    # email
    # logging
```

Prefer:

```python
@router.post("/customers")
def create_customer(request, service):
    return service.create(request)
```

## Avoid Premature Abstraction

Do not create:

* interfaces without a purpose,
* factories without complexity,
* generic repositories without a real requirement,
* unnecessary base classes,
* excessive layers.

Start simple and introduce abstractions when the problem justifies them.
