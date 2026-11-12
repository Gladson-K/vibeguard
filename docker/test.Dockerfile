FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/gateway

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ curl bash \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements-test.txt /tmp/requirements-test.txt
COPY gateway/requirements.txt /tmp/gateway-requirements.txt
RUN pip install --no-cache-dir -r /tmp/gateway-requirements.txt -r /tmp/requirements-test.txt

WORKDIR /app
COPY . /app
RUN chmod +x docker/*.sh && bash docker/build_sil.sh

CMD ["pytest", "-q"]
