FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /sandbox

RUN useradd --create-home --uid 10001 sandbox
USER sandbox

EXPOSE 8080

COPY healthcheck.py /sandbox/healthcheck.py
COPY server.py /sandbox/server.py

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 CMD ["python", "/sandbox/healthcheck.py"]

CMD ["python", "/sandbox/server.py"]
