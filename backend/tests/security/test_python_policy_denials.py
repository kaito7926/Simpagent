from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def sandbox_root() -> Path:
    local_root = Path(__file__).resolve().parents[3] / "sandbox"
    if local_root.exists():
        return local_root
    mounted_root = Path("/workspace/sandbox")
    assert mounted_root.exists()
    return mounted_root


def load_module(relative_path: str, module_name: str):
    module_path = sandbox_root() / relative_path
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def build_spec(runner, code: str):
    temp_dir = TemporaryDirectory()
    workspace = Path(temp_dir.name)
    spec = runner.RunSpec(
        execution_id="exec-policy-001",
        profile_name="python-basic-v1",
        code=code,
        workspace_dir=str(workspace),
        artifact_dir=str(workspace / "artifacts"),
        result_path=str(workspace / "result.json"),
        output_limit_bytes=16 * 1024,
        artifact_limit_bytes=128 * 1024,
        max_artifacts=4,
    )
    return temp_dir, spec


def test_blocked_non_allowlisted_import_returns_policy_error_and_no_artifacts() -> None:
    runner = load_module("runtime/runner.py", "sandbox_runner_policy_import")
    temp_dir, spec = build_spec(runner, "import requests\nprint('should not run')\n")
    try:
        result = runner.execute_run_spec(spec)
    finally:
        temp_dir.cleanup()

    assert result["status"] == "policy_error"
    assert result["policy_error_code"] == "blocked_import"
    assert result["artifacts"] == []


def test_package_install_and_external_command_attempts_are_rejected() -> None:
    runner = load_module("runtime/runner.py", "sandbox_runner_policy_commands")
    temp_dir, spec = build_spec(runner, "import os\nos.system('pip install requests')\n")
    try:
        result = runner.execute_run_spec(spec)
    finally:
        temp_dir.cleanup()

    assert result["status"] == "policy_error"
    assert result["policy_error_code"] == "disallowed_behavior"
    assert result["artifacts"] == []
