# CLAUDE.md

Guia para agentes de IA ao trabalhar com o código deste repositório.

Este projeto é um **monorepo em python que serve com uma API para aplicação de RAG (retrieval augmented generation)**

## Tecnologias
- Python 3.11.x with FastAPI
- Postgresql
- API chatGPT
- Redis
- LangChain

## Python Virtual Environment

This project must always use the project's Python virtual environment.
The virtual environment is located at: .venv/

Never install Python packages globally.
Before running Python commands, tests, linters, formatters, or application scripts, make sure the .venv environment is being used.

### Prioridades

- **Sempre verifique as instruções dentro de ./claude/code_patterns** antes de implementar qualquer modificação
- Do not introduce architectural patterns, dependencies, or abstractions without a clear reason.

### General Rules
- Use asynchronous methods
- Use FastAPI for build the application
- Use logs into the application, never print messages with 'print("..")'
- **ALWAYS PREFER USING TYPING THROUGHOUT THE CODE. USE MODELS/OBJECTS AND PRIMITIVE TYPES**
- Keep all code structure and logic segregated 
- Prefer simple, readable, maintainable code.
- Follow the existing project architecture.
- Reuse existing components before creating new ones.
- Avoid unnecessary abstractions.
- Do not duplicate existing functionality.
- Do not modify unrelated code.
- Keep changes focused on the requested task.
- Do not change public APIs or contracts unless explicitly required.
- Do not remove existing functionality without a clear requirement.
- Avoid methods with more than 30 lines
- Always use the 'clean code' concept
- Don't overuse abstractions if there is just one implementation.
- **NEVER USE SENSITIVE DATA HARDCODED IN THE CODE**
- **ALWAYS USE A CONFIGURATION FILE FOR DYNAMIC INFORMATION**
- **ALWAYS USE ENVIRONMENT VARIABLES FOR SENSITIVE INFORMATION AND CONFIDENTIAL DATA**

### Project Structure

The project follows this general structure:

src/
├── domain/ (entidades e modelos)
├── application/
├── infrastructure/
└── api/
├── helpers/

tests/
├── unit/


## Architecture

Business logic should remain independent from infrastructure concerns.

Follow the architecture guidelines defined in:

- `.agents/code_patterns/architecture.md`

Do not introduce new layers or abstractions unless they provide a clear benefit.

## Coding Standards

Follow:

- `.agents/code_patterns/python-conventions.md`

Use the project's existing formatter, linter, and type checker.

Do not introduce a new code-quality tool without a specific reason.

## Testing

Every behavior change should have appropriate tests.

Follow:

- `.agents/code_patterns/testing.md`

Before considering a task complete:

1. Run relevant unit tests.
2. Run relevant integration tests when applicable.
3. Run configured linting.
4. Run configured type checking.
5. Fix failures caused by the changes.

Do not modify tests simply to make them pass unless the existing test is incorrect.

## Error Handling

Follow:

- `.agents/code_patterns/error-handling.md`

Do not silently swallow exceptions.

Do not expose internal implementation details through APIs.

## Security

Follow:

- `.agents/code_patterns/security.md`

Never commit:

- passwords,
- API keys,
- tokens,
- private keys,
- credentials,
- sensitive configuration.

## Dependencies

Before adding a dependency:

1. Check whether the standard library can solve the problem.
2. Check whether an existing dependency can solve it.
3. Consider maintenance and security implications.
4. Add the dependency only when justified.

Do not update unrelated dependencies.

## Working Process

When implementing a task:

1. Understand the existing code.
2. Identify the relevant components.
3. Check existing patterns before creating new ones.
4. Implement the smallest appropriate change.
5. Add or update tests.
6. Run validation tools.
7. Review the final diff.
8. Report what changed and any relevant limitations.

### Comandos do projeto
- **SEMPRE EXECUTE OS COMANDOS DENTRO DO venv**

```bash
python -m venv .venv            #Create the virtual environment if it does not existi
.venv\Scripts\python.exe        # Active the virtual environment
pip install -r requirements.txt # Install dependences
python main.py                  # Run the application
python -m build                 # Build the application
python -m pytest                # Run the application tests
```
