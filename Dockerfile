# Microservicio Docker independiente del mock_starlink (ADR-07). python:3.11-slim
# es multi-arch (amd64/arm64) — corre igual en la PC de desarrollo y en el RPi5
# de semana 10 (ADR-05, ADR-12) sin cambios.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "mock_starlink"]
