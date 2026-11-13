FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir platformio

WORKDIR /app/firmware
COPY firmware/ ./

# Compile-only gate for the ESP32-S3 target (no device / upload needed).
RUN pio run -e esp32s3
