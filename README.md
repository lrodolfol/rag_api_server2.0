# rag_api_server2.0

(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& c:\Users\rodolfo.jesus\Documents\ti-nos-negocios\acha_local\rag_api_server2.0\.venv\Scripts\Activate.ps1)

uvicorn app.main:app --reload

launch.json
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI: main.py (debug)",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/Scripts/python.exe",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false
    },
    {
      "name": "FastAPI: uvicorn --reload",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--log-level",
        "debug"
      ],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/Scripts/python.exe",
      "envFile": "${workspaceFolder}/.env",
      "subProcess": true,
      "justMyCode": false
    },
    {
      "name": "Pytest: arquivo atual",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-vv", "-s"],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/Scripts/python.exe",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false
    },
    {
      "name": "Pytest: todos os testes",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["-vv"],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/Scripts/python.exe",
      "envFile": "${workspaceFolder}/.env",
      "justMyCode": false
    }
  ]
}
```

settings.json
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"]
}
```