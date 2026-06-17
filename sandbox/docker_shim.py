#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, BuildError, DockerException, ImageNotFound, NotFound


class CliError(RuntimeError):
    pass


def _stderr(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _client():
    return docker.from_env(version="auto")


def _require_value(args: list[str], index: int, option: str) -> str:
    try:
        return args[index + 1]
    except IndexError as exc:
        raise CliError(f"Missing value for {option}.") from exc


def _parse_key_value_pairs(items: list[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise CliError(f"Expected KEY=VALUE syntax, got {item!r}.")
        key, value = item.split("=", 1)
        pairs[key] = value
    return pairs


def _parse_tmpfs(items: list[str]) -> dict[str, str]:
    tmpfs: dict[str, str] = {}
    for item in items:
        path, _, options = item.partition(":")
        tmpfs[path] = options
    return tmpfs


def _parse_extra_hosts(items: list[str]) -> dict[str, str]:
    entries: dict[str, str] = {}
    for item in items:
        host, _, value = item.partition(":")
        if not host or not value:
            raise CliError(f"Expected host:ip syntax, got {item!r}.")
        entries[host] = value
    return entries


def _coerce_explanation(error: Exception) -> str:
    if isinstance(error, APIError):
        explanation = error.explanation
        if isinstance(explanation, bytes):
            return explanation.decode("utf-8", errors="replace")
        if explanation:
            return str(explanation)
    return str(error)


def _build(client, args: list[str]) -> int:
    dockerfile: str | None = None
    tag: str | None = None
    context: str | None = None
    index = 0

    while index < len(args):
        token = args[index]
        if token == "-f":
            dockerfile = _require_value(args, index, token)
            index += 2
            continue
        if token == "-t":
            tag = _require_value(args, index, token)
            index += 2
            continue
        if token.startswith("-"):
            raise CliError(f"Unsupported docker build option {token!r}.")
        context = token
        index += 1
        break

    if context is None or index != len(args):
        raise CliError("docker build expects a single build context path.")

    context_path = Path(context).resolve()
    dockerfile_path = (Path(dockerfile).resolve() if dockerfile else context_path / "Dockerfile")
    try:
        dockerfile_rel = dockerfile_path.relative_to(context_path)
    except ValueError as exc:
        raise CliError("Build Dockerfile must live inside the build context.") from exc

    try:
        stream = client.api.build(
            path=str(context_path),
            dockerfile=str(dockerfile_rel),
            tag=tag,
            rm=True,
            decode=True,
        )
        for chunk in stream:
            if "error" in chunk:
                raise CliError(str(chunk["error"]))
            if "stream" in chunk:
                sys.stdout.write(str(chunk["stream"]))
    except BuildError as exc:
        raise CliError(_coerce_explanation(exc)) from exc
    return 0


def _image_inspect(client, args: list[str]) -> int:
    if len(args) != 1:
        raise CliError("docker image inspect expects exactly one image reference.")
    try:
        payload = client.api.inspect_image(args[0])
    except ImageNotFound:
        return 1
    sys.stdout.write(json.dumps([payload]))
    return 0


def _create(client, args: list[str]) -> int:
    name: str | None = None
    network_mode: str | None = None
    user: str | None = None
    pids_limit: int | None = None
    mem_limit: int | None = None
    nano_cpus: int | None = None
    read_only = False
    cap_drop: list[str] = []
    security_opt: list[str] = []
    tmpfs: list[str] = []
    binds: list[str] = []
    devices: list[str] = []
    dns: list[str] = []
    extra_hosts: list[str] = []
    environment: list[str] = []
    labels: list[str] = []
    image: str | None = None
    command: list[str] = []

    index = 0
    while index < len(args):
        token = args[index]
        if token == "--name":
            name = _require_value(args, index, token)
            index += 2
            continue
        if token == "--network":
            network_mode = _require_value(args, index, token)
            index += 2
            continue
        if token == "--user":
            user = _require_value(args, index, token)
            index += 2
            continue
        if token == "--pids-limit":
            pids_limit = int(_require_value(args, index, token))
            index += 2
            continue
        if token == "--memory":
            mem_limit = int(_require_value(args, index, token))
            index += 2
            continue
        if token == "--cpus":
            nano_cpus = int(float(_require_value(args, index, token)) * 1_000_000_000)
            index += 2
            continue
        if token == "--read-only":
            read_only = True
            index += 1
            continue
        if token == "--cap-drop":
            cap_drop.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--security-opt":
            security_opt.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--tmpfs":
            tmpfs.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--volume":
            binds.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--device":
            devices.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--dns":
            dns.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--add-host":
            extra_hosts.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--env":
            environment.append(_require_value(args, index, token))
            index += 2
            continue
        if token == "--label":
            labels.append(_require_value(args, index, token))
            index += 2
            continue
        if token.startswith("-"):
            raise CliError(f"Unsupported docker create option {token!r}.")
        image = token
        command = args[index + 1 :]
        break

    if image is None:
        raise CliError("docker create requires an image name.")

    host_config_kwargs: dict[str, Any] = {
        "network_mode": network_mode,
        "read_only": read_only,
        "cap_drop": cap_drop or None,
        "security_opt": security_opt or None,
        "tmpfs": _parse_tmpfs(tmpfs) or None,
        "binds": binds or None,
        "devices": devices or None,
        "dns": dns or None,
        "extra_hosts": _parse_extra_hosts(extra_hosts) or None,
        "pids_limit": pids_limit,
        "mem_limit": mem_limit,
        "nano_cpus": nano_cpus,
    }
    host_config_kwargs = {key: value for key, value in host_config_kwargs.items() if value is not None}

    try:
        host_config = client.api.create_host_config(**host_config_kwargs)
    except TypeError:
        fallback = dict(host_config_kwargs)
        fallback.pop("nano_cpus", None)
        host_config = client.api.create_host_config(**fallback)
        if nano_cpus is not None:
            host_config["NanoCpus"] = nano_cpus

    payload = client.api.create_container(
        image=image,
        command=command or None,
        name=name,
        host_config=host_config,
        environment=environment or None,
        labels=_parse_key_value_pairs(labels) or None,
        user=user,
    )
    sys.stdout.write(str(payload.get("Id", "")))
    return 0


def _start(client, args: list[str]) -> int:
    if len(args) != 1:
        raise CliError("docker start expects exactly one container name.")
    client.api.start(args[0])
    return 0


def _wait(client, args: list[str]) -> int:
    if len(args) != 1:
        raise CliError("docker wait expects exactly one container name.")
    payload = client.api.wait(args[0])
    sys.stdout.write(f"{payload.get('StatusCode', '')}\n")
    return 0


def _kill(client, args: list[str]) -> int:
    if len(args) != 1:
        raise CliError("docker kill expects exactly one container name.")
    client.api.kill(args[0])
    return 0


def _rm(client, args: list[str]) -> int:
    force = False
    names: list[str] = []
    for token in args:
        if token == "-f":
            force = True
            continue
        if token.startswith("-"):
            raise CliError(f"Unsupported docker rm option {token!r}.")
        names.append(token)
    if len(names) != 1:
        raise CliError("docker rm expects exactly one container name.")
    client.api.remove_container(names[0], force=force)
    return 0


def _logs(client, args: list[str]) -> int:
    if len(args) != 1:
        raise CliError("docker logs expects exactly one container name.")
    output = client.api.logs(args[0], stdout=True, stderr=True)
    if isinstance(output, bytes):
        sys.stdout.buffer.write(output)
    else:
        sys.stdout.write(str(output))
    return 0


def _cp(client, args: list[str]) -> int:
    if len(args) != 2 or ":" not in args[0]:
        raise CliError("docker cp expects SOURCE as container:path and a destination path.")
    container_name, source_path = args[0].split(":", 1)
    destination = Path(args[1])

    stream, _ = client.api.get_archive(container_name, source_path)
    archive = io.BytesIO(b"".join(stream))
    with tarfile.open(fileobj=archive, mode="r:*") as tar:
        member = next((item for item in tar.getmembers() if item.isfile()), None)
        if member is None:
            raise CliError("docker cp could not find a file payload in the returned archive.")
        extracted = tar.extractfile(member)
        if extracted is None:
            raise CliError("docker cp could not extract the requested file.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(extracted.read())
    return 0


def _version() -> int:
    sys.stdout.write("Docker shim via Python SDK\n")
    return 0


def _daemon_version(client) -> int:
    payload = client.api.version()
    sys.stdout.write(json.dumps(payload))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _stderr("docker shim requires a command.")
        return 1
    if args == ["--version"]:
        return _version()

    command = args.pop(0)
    try:
        client = _client()
        if command == "build":
            return _build(client, args)
        if command == "create":
            return _create(client, args)
        if command == "start":
            return _start(client, args)
        if command == "wait":
            return _wait(client, args)
        if command == "kill":
            return _kill(client, args)
        if command == "rm":
            return _rm(client, args)
        if command == "logs":
            return _logs(client, args)
        if command == "cp":
            return _cp(client, args)
        if command == "version":
            return _daemon_version(client)
        if command == "image" and args[:1] == ["inspect"]:
            return _image_inspect(client, args[1:])
        raise CliError(f"Unsupported docker command {command!r}.")
    except (CliError, DockerException, APIError, NotFound) as exc:
        _stderr(_coerce_explanation(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
