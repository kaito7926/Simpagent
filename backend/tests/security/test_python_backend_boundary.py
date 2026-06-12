from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "app"

FORBIDDEN_NAME_CALLS = {"exec", "eval", "compile"}
FORBIDDEN_ATTRIBUTE_CALLS = {
    ("os", "system"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
}
FORBIDDEN_IMPORTS = {"subprocess"}


class ForbiddenExecutionVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.offenders: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".", 1)[0] in FORBIDDEN_IMPORTS:
                self.offenders.append(f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".", 1)[0] in FORBIDDEN_IMPORTS:
            self.offenders.append(f"from {node.module} import ...")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAME_CALLS:
            self.offenders.append(f"{node.func.id}()")
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            candidate = (node.func.value.id, node.func.attr)
            if candidate in FORBIDDEN_ATTRIBUTE_CALLS:
                self.offenders.append(f"{candidate[0]}.{candidate[1]}()")
        self.generic_visit(node)


def iter_backend_sources() -> list[Path]:
    return sorted(path for path in APP_ROOT.rglob("*.py") if path.is_file())


def test_backend_app_contains_no_direct_python_execution_surface() -> None:
    offenders: dict[str, list[str]] = {}

    for path in iter_backend_sources():
        visitor = ForbiddenExecutionVisitor()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        if visitor.offenders:
            offenders[str(path.relative_to(ROOT))] = visitor.offenders

    assert offenders == {}
