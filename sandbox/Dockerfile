FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /sandbox

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates docker.io \
    && pip install --no-cache-dir "docker>=7,<8" \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

COPY healthcheck.py /sandbox/healthcheck.py
COPY server.py /sandbox/server.py
COPY docker_shim.py /usr/local/bin/docker
COPY runtime /sandbox/runtime
COPY seccomp /opt/simpagent/seccomp

RUN chmod +x /usr/local/bin/docker

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 CMD ["python", "/sandbox/healthcheck.py"]

CMD ["python", "/sandbox/server.py"]
