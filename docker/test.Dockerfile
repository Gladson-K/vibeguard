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
# NAS-select the best autoencoder, export int8 TinyML weights, then build SIL nodes.
RUN chmod +x docker/*.sh \
    && python -m tools.train_autoencoder --quick --out /app/models/tinyml \
    && bash docker/build_sil.sh

CMD ["pytest", "-q"]
