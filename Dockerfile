# Single image for both demo Python services (producer + runner).
# The start command is overridden per service at deploy time, so one
# build artifact serves both Render web services.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the SDK first so its dependency layer caches separately from the
# (frequently-changing) demo source.
COPY sdk/python /app/sdk/python
RUN pip install /app/sdk/python

# Demo entrypoints (producer.py + runner.py) live here.
COPY demo /app/demo

# Producer = 8000, runner = 8001 — Render injects PORT, so each service
# overrides this CMD with the correct uvicorn target. Default is the
# runner because that is what the hosted frontend talks to.
ENV PORT=8001
CMD ["sh", "-c", "uvicorn demo.runner:app --host 0.0.0.0 --port ${PORT}"]
