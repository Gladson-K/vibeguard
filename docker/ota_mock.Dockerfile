FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY tools/ota_sign.py tools/ota_server.py /app/tools/
RUN chmod +x /app/tools/ota_server.py

EXPOSE 8080
CMD ["python", "/app/tools/ota_server.py", "--port", "8080", "--dir", "/tmp/ota"]
