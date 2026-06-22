from __future__ import annotations

import re
from enum import Enum


PYTHON_SUMMARY_MAX_CHARS = 512
PYTHON_OUTPUT_EXCERPT_MAX_CHARS = 8192
PYTHON_STATE_MAX_BYTES = 256 * 1024
PYTHON_ARTIFACT_MAX_BYTES = 512 * 1024
PYTHON_STATE_SCHEMA_VERSION = 1
SAFE_ARTIFACT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class PythonExecutionStatus(str, Enum):
    accepted = "accepted"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    denied = "denied"
    policy_error = "policy_error"
    limit_reached = "limit_reached"
    infra_failure = "infra_failure"


class PythonExecutionProfile(str, Enum):
    basic = "python-basic-v1"
    data = "python-data-v1"


class PythonArtifactType(str, Enum):
    csv = "csv"
    json = "json"
    txt = "txt"
    png = "png"


class PythonLimitName(str, Enum):
    wall_time = "wall_time"
    cpu = "cpu"
    memory = "memory"
    pid_count = "pid_count"
    process_count = "process_count"
    file_size = "file_size"
    output_size = "output_size"


class PythonDeniedReason(str, Enum):
    missing_permission = "missing_permission"
    search_required = "search_required"
    policy_denied = "policy_denied"


class PythonPolicyErrorCode(str, Enum):
    blocked_import = "blocked_import"
    disallowed_behavior = "disallowed_behavior"


class PythonInfraFailureReason(str, Enum):
    worker_start_failed = "worker_start_failed"
    worker_unavailable = "worker_unavailable"
