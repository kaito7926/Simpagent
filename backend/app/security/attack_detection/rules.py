from __future__ import annotations

import re

from .schemas import AttackRule, AttackSignal

_DEFAULT_FLAGS = re.IGNORECASE


def _signal(signal_id: str, name: str, pattern: str, description: str) -> AttackSignal:
    return AttackSignal(
        signal_id=signal_id,
        name=name,
        pattern=re.compile(pattern, _DEFAULT_FLAGS),
        description=description,
    )


DEFAULT_ATTACK_RULES: tuple[AttackRule, ...] = (
    AttackRule(
        rule_id="reverse_shell.python_socket_shell",
        name="Python reverse shell",
        category="reverse_shell",
        severity="critical",
        description="Combines socket callback, descriptor redirection, and shell spawn signals.",
        min_signal_hits=3,
        signals=(
            _signal(
                "socket_connect",
                "Socket callback",
                r"(?:\bsocket\.(?:socket|create_connection)\s*\(|\.\s*connect\s*\()",
                "Opens an outbound socket connection used as a callback channel.",
            ),
            _signal(
                "fd_redirect",
                "Descriptor redirection",
                r"\b(?:os\.)?dup2\s*\(",
                "Redirects stdin/stdout/stderr to another file descriptor.",
            ),
            _signal(
                "interactive_shell",
                "Interactive shell spawn",
                r"(?:/bin/(?:ba)?sh\b|cmd\.exe\b|powershell(?:\.exe)?\b|\bpty\.spawn\s*\()",
                "Spawns an interactive shell process.",
            ),
        ),
    ),
    AttackRule(
        rule_id="reverse_shell.one_liner",
        name="Reverse shell one-liner",
        category="reverse_shell",
        severity="critical",
        description="Detects classic bash, netcat, or socat reverse shell one-liners.",
        min_signal_hits=1,
        signals=(
            _signal(
                "bash_tcp_redirect",
                "Bash TCP redirect",
                r"\bbash\s+-i\b.*?/dev/tcp/[^/\s]+/\d+",
                "Uses bash TCP redirection for a reverse shell.",
            ),
            _signal(
                "netcat_exec",
                "Netcat exec shell",
                r"\b(?:nc|netcat)\b[^\n]*\s-e\s+/bin/(?:ba)?sh\b",
                "Uses netcat with -e to hand out a shell.",
            ),
            _signal(
                "socat_exec",
                "Socat exec shell",
                r"\bsocat\b[^\n]*exec:(?:['\"])?/bin/(?:ba)?sh\b",
                "Uses socat to bind a shell to a socket.",
            ),
        ),
    ),
    AttackRule(
        rule_id="ssrf.internal_target",
        name="Internal SSRF target",
        category="ssrf",
        severity="high",
        description="Pairs an HTTP client with localhost, metadata, or RFC1918 targets.",
        min_signal_hits=2,
        signals=(
            _signal(
                "network_client",
                "Network client",
                r"\b(?:requests|httpx)\.(?:get|post|put|delete|request)\s*\(|urllib\.request\.urlopen\s*\(|\bcurl\s+https?://",
                "Uses a scriptable HTTP client or curl.",
            ),
            _signal(
                "internal_target",
                "Internal target",
                r"\b(?:169\.254\.169\.254|metadata\.google\.internal|localhost|127\.0\.0\.1|0\.0\.0\.0|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b",
                "Targets metadata, loopback, or private network addresses.",
            ),
        ),
    ),
    AttackRule(
        rule_id="secret_exfiltration.env_to_network",
        name="Secret exfiltration",
        category="secret_exfiltration",
        severity="high",
        description="Combines sensitive secret access with an outbound network sink.",
        min_signal_hits=2,
        signals=(
            _signal(
                "secret_read",
                "Secret read",
                r"\bos\.(?:getenv|environ\.get)\s*\(\s*[\"'][A-Z0-9_]*(?:TOKEN|SECRET|API[_-]?KEY|PASSWORD|COOKIE|JWT|BEARER)[A-Z0-9_]*[\"']\s*\)|\bos\.environ\[\s*[\"'][A-Z0-9_]*(?:TOKEN|SECRET|API[_-]?KEY|PASSWORD|COOKIE|JWT|BEARER)[A-Z0-9_]*[\"']\s*\]|\b(?:OPENAI_API_KEY|GOOGLE_API_KEY|AWS_SECRET_ACCESS_KEY|ACCESS_TOKEN|REFRESH_TOKEN|JWT_SECRET)\b",
                "Reads a credential-like value from environment or a known secret name.",
            ),
            _signal(
                "network_sink",
                "Network sink",
                r"\b(?:requests|httpx)\.(?:post|put|request)\s*\(|urllib\.request\.urlopen\s*\(|\bcurl\s+-[dF]\b",
                "Sends data to a remote endpoint.",
            ),
        ),
    ),
    AttackRule(
        rule_id="sensitive_file_access.host_secrets",
        name="Sensitive host file access",
        category="sensitive_file_access",
        severity="high",
        description="References high-signal file paths used to collect credentials or host state.",
        min_signal_hits=1,
        signals=(
            _signal(
                "unix_account_db",
                "Unix account database",
                r"/etc/(?:passwd|shadow)\b",
                "Reads core Unix account databases.",
            ),
            _signal(
                "proc_environ",
                "Process environment",
                r"/proc/(?:self|1)/environ\b",
                "Reads environment variables from a process procfs entry.",
            ),
            _signal(
                "ssh_private_key",
                "SSH private key",
                r"\.ssh/(?:id_rsa|id_ed25519)\b",
                "Touches a common SSH private key path.",
            ),
            _signal(
                "service_account_token",
                "Service account token",
                r"/(?:var/)?run/secrets/[^\"'\s]+",
                "Touches a runtime secret mount.",
            ),
            _signal(
                "windows_sam",
                "Windows SAM",
                r"(?:[a-z]:\\\\)?windows\\\\system32\\\\config\\\\sam\b",
                "Touches the Windows SAM credential database.",
            ),
        ),
    ),
    AttackRule(
        rule_id="container_escape.docker_socket_or_host_namespace",
        name="Container escape primitive",
        category="container_escape",
        severity="critical",
        description="References the Docker socket, host namespaces, or privileged host mounts.",
        min_signal_hits=1,
        signals=(
            _signal(
                "docker_socket",
                "Docker socket",
                r"/var/run/docker\.sock\b",
                "Touches the Docker daemon socket.",
            ),
            _signal(
                "host_root_mount",
                "Host root mount",
                r"\bdocker\s+run\b[^\n]*(?:--privileged\b|(?:-v|--volume)\s+/\s*:\s*/host\b)",
                "Launches a privileged container or mounts the host root filesystem.",
            ),
            _signal(
                "nsenter",
                "Namespace entry",
                r"\bnsenter\b",
                "Enters another process namespace.",
            ),
            _signal(
                "proc_root",
                "Proc root traversal",
                r"/proc/1/root\b",
                "Traverses the host root through PID 1 procfs.",
            ),
        ),
    ),
    AttackRule(
        rule_id="privilege_escalation.suid_or_capabilities",
        name="Privilege escalation primitive",
        category="privilege_escalation",
        severity="high",
        description="Uses SUID bits, Linux capabilities, or administrator-group mutation.",
        min_signal_hits=1,
        signals=(
            _signal(
                "suid_bit",
                "SUID bit set",
                r"\bchmod\s+(?:u\+s|[0-7]?4[0-7]{2})\b",
                "Sets the SUID bit on a file.",
            ),
            _signal(
                "linux_capabilities",
                "Linux capabilities",
                r"\bsetcap\s+cap_[a-z0-9_,+=-]+",
                "Adds elevated Linux capabilities to a binary.",
            ),
            _signal(
                "pkexec",
                "pkexec",
                r"\bpkexec\b",
                "Invokes the pkexec escalation path.",
            ),
            _signal(
                "windows_admin_group",
                "Windows admin group mutation",
                r"\bnet\s+localgroup\s+administrators\b",
                "Mutates Windows administrator group membership.",
            ),
        ),
    ),
)

__all__ = ["DEFAULT_ATTACK_RULES"]
