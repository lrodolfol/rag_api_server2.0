# Testing Guidelines

## General Principles

Tests should provide confidence that the software behaves as expected.

Prefer:

* Small tests.
* Deterministic tests.
* Fast unit tests.
* Clear test names.
* One behavior per test.
* Independent tests.

Avoid tests that depend on execution order.

## Test Structure

Organize tests according to the application structure when appropriate.

Example:

```text
tests/
├── unit/
│   ├── domain/
│   ├── services/
│   └── repositories/
│
└── integration/
    ├── api/
    └── database/
```

## Naming

Test names should describe the expected behavior.

Prefer:

```python
def test_should_return_customer_when_id_exists():
    ...
```

Instead of:

```python
def test_customer():
    ...
```

## Arrange, Act, Assert

Prefer the AAA pattern:

```python
def test_should_calculate_total():
    # Arrange
    price = 100
    quantity = 2

    # Act
    result = calculate_total(price, quantity)

    # Assert
    assert result == 200
```

## Unit Tests

Unit tests should test one component in isolation.

Avoid unnecessary database, network, filesystem, or external service dependencies in unit tests.

Use mocks only when they provide value.

Do not mock everything.

## Integration Tests

Use integration tests when validating interactions between components such as:

* Database.
* HTTP APIs.
* Message brokers.
* External services.
* Application infrastructure.

Integration tests should use isolated test resources whenever possible.

## External Services

Do not make real calls to production services during automated tests.

Use:

* mocks,
* fakes,
* local containers,
* test environments,
* or dedicated test services.

## Test Coverage

Coverage is a useful indicator but should not be treated as the only measure of quality.

Prioritize testing:

* Business rules.
* Edge cases.
* Error handling.
* Important integrations.
* Critical workflows.

Avoid writing meaningless tests solely to increase coverage.
