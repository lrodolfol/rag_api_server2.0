# API Guidelines

- Use FastAPI for build the application
- Maintain a rate limit for security application
- Use asynchronous methods
- The API routes should be located in `./app/api/routes`
- All response API should have the same structure:
```json
{
    "status_code": 200,
    "message": "some message",
    "errors": [
        "error 1",
        "error 2"
    ]
}
```
create it in `./app/api/patterns/response.py`
- Always work with type
- Avoid coupling
- Maintain a basic health-check structure in `./app/routes/health.py`
- Maintain the dependecies injections into `./app/dependencies.py`
- Maintain the schemas into `./app/schemas.py` if necessary