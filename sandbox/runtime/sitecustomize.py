from __future__ import annotations

import os
import socket
import subprocess
from typing import Any


class SandboxPolicyError(RuntimeError):
    pass


def _blocked(message: str):
    def blocker(*args: Any, **kwargs: Any):
        raise SandboxPolicyError(message)

    return blocker


for variable_name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(variable_name, None)

subprocess.run = _blocked("External command execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
subprocess.Popen = _blocked("External command execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
subprocess.call = _blocked("External command execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
subprocess.check_call = _blocked("External command execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
subprocess.check_output = _blocked("External command execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
os.system = _blocked("Shell execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
os.popen = _blocked("Shell execution is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
for _os_attr in (
    "_exit",
    "abort",
    "execv",
    "execve",
    "execvp",
    "execvpe",
    "fork",
    "forkpty",
    "kill",
    "killpg",
    "posix_spawn",
    "posix_spawnp",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
):
    if hasattr(os, _os_attr):
        setattr(os, _os_attr, _blocked("Process control is blocked in the reviewed Python sandbox."))
socket.socket = _blocked("Network access is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
socket.create_connection = _blocked("Network access is blocked in the reviewed Python sandbox.")  # type: ignore[assignment]
