FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /runtime

RUN useradd --create-home --uid 10002 --shell /usr/sbin/nologin runner \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir numpy pandas matplotlib

COPY runner.py /runtime/runner.py
COPY sitecustomize.py /runtime/sitecustomize.py
COPY allowed_artifacts.py /runtime/allowed_artifacts.py

ENV PYTHONPATH=/runtime \
    MPLBACKEND=Agg

USER 10002:10002

CMD ["python", "/runtime/runner.py"]
