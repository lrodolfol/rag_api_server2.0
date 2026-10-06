"""Guard test: the domain layer must not depend on frameworks/infrastructure.

Scans the imports of every module under ``app/domain`` and fails if a forbidden
dependency (FastAPI, boto3, provider/HTTP clients, etc.) is imported, keeping
the domain independently testable.
"""

import ast
from pathlib import Path

import pytest

DOMAIN_DIR = Path(__file__).resolve().parents[3] / "app" / "domain"

FORBIDDEN_ROOTS = {
    "fastapi",
    "starlette",
    "boto3",
    "botocore",
    "openai",
    "pinecone",
    "redis",
    "langchain",
    "httpx",
    "requests",
}

DOMAIN_FILES = sorted(DOMAIN_DIR.glob("*.py"))


def _imported_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module_path", DOMAIN_FILES, ids=lambda p: p.name)
def test_domain_module_has_no_forbidden_imports(module_path: Path) -> None:
    # Arrange
    source = module_path.read_text(encoding="utf-8")

    # Act
    roots = _imported_roots(source)

    # Assert
    assert not (roots & FORBIDDEN_ROOTS), (
        f"{module_path.name} imports forbidden dependency: {roots & FORBIDDEN_ROOTS}"
    )
