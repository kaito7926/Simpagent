from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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


def test_supervisor_launch_spec_disables_network_and_has_no_host_escape_surface() -> None:
    server = load_module("server.py", "sandbox_server_network")
    request = server.ExecutionRequest(
        execution_id="exec-network-001",
        capability=server.issue_capability_token(
            execution_id="exec-network-001",
            profile_name="python-basic-v1",
            code="print('hello')",
        ),
        profile_name="python-basic-v1",
        code="print('hello')",
    )

    launch_spec = server.build_runtime_launch_spec(request)
    assert launch_spec.network_mode == "none"
    assert launch_spec.bind_mounts == ()
    assert launch_spec.devices == ()
    assert launch_spec.dns == ()
    assert launch_spec.extra_hosts == ()


def test_network_targets_are_denied_before_any_runtime_network_path_exists() -> None:
    runner = load_module("runtime/runner.py", "sandbox_runner_network")
    targets = {
        "http://127.0.0.1:8000/health": "localhost",
        "http://10.0.0.5/private": "private address",
        "http://169.254.169.254/latest/meta-data": "metadata address",
        "http://backend:8000/internal": "internal service name",
    }

    for target, _label in targets.items():
        review = runner.review_python_source(
            f"import urllib.request\nurllib.request.urlopen('{target}')\n"
        )
        assert review.allowed is False
        assert review.policy_error_code == "blocked_import"
        assert review.blocked_symbol == "urllib"
