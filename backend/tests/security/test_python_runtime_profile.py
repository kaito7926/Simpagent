from __future__ import annotations

import importlib.util
import json
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


def test_runtime_profiles_are_backend_owned_and_fixed() -> None:
    server = load_module("server.py", "sandbox_server_profiles")

    assert set(server.PROFILES) == {"python-basic-v1", "python-data-v1"}
    assert server.PROFILES["python-basic-v1"].memory_bytes < server.PROFILES["python-data-v1"].memory_bytes
    assert server.PROFILES["python-basic-v1"].wall_time_seconds < server.PROFILES["python-data-v1"].wall_time_seconds


def test_runtime_launch_spec_enforces_non_root_read_only_and_no_new_privileges() -> None:
    server = load_module("server.py", "sandbox_server_profile_spec")
    request = server.ExecutionRequest(
        execution_id="exec-profile-001",
        capability=server.issue_capability_token(
            execution_id="exec-profile-001",
            profile_name="python-data-v1",
            code="print('profile')",
        ),
        profile_name="python-data-v1",
        code="print('profile')",
    )

    launch_spec = server.build_runtime_launch_spec(request)
    assert launch_spec.user == "10002:10002"
    assert launch_spec.read_only_rootfs is True
    assert launch_spec.cap_drop == ("ALL",)
    assert "no-new-privileges" in launch_spec.security_opt
    assert all(not option.startswith("seccomp=") for option in launch_spec.security_opt)
    assert launch_spec.pids_limit == server.PROFILES["python-data-v1"].pids_limit
    assert launch_spec.memory_bytes == server.PROFILES["python-data-v1"].memory_bytes
    assert launch_spec.nano_cpus == server.PROFILES["python-data-v1"].nano_cpus
    assert any("noexec" in mount for mount in launch_spec.tmpfs_mounts)


def test_reviewed_seccomp_asset_is_present_and_fixed() -> None:
    payload = json.loads((sandbox_root() / "seccomp" / "python-restricted.json").read_text(encoding="utf-8"))

    assert payload["profile_name"] == "python-restricted"
    assert payload["base_profile"] == "docker-default"
    assert payload["defaultAction"] == "SCMP_ACT_ERRNO"
