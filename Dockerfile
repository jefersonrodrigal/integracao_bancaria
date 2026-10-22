FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

RUN useradd --create-home --uid 10001 app

COPY requirements.lock pyproject.toml README.md ./
RUN pip install -r requirements.lock

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
RUN pip install --no-deps . && mkdir -p /srv/data/files && chown -R app /srv/data

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

# TLS deve ser terminado no proxy reverso/balanceador à frente deste contêiner.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
