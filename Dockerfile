# eon-core — Docker
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY config/ taiji.yaml

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "src.main", "--config", "taiji.yaml", "health"]
