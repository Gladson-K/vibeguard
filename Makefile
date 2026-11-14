COMPOSE ?= docker-compose -f docker/docker-compose.yml
REPORT_DIR ?= reports

.PHONY: help up down logs test-v1 test-v2 test-v3 test-ml test-all build-firmware clean reports

help:
	@echo "VibeGuard targets:"
	@echo "  make up              start gateway + mosquitto (dashboard on :8000)"
	@echo "  make test-v1         full V1 E2E suite in Docker"
	@echo "  make test-v2         full V2 E2E suite in Docker"
	@echo "  make test-v3         V3 OTA/power/prodtest suite in Docker"
	@echo "  make test-ml         full NAS TinyML training (non-quick)"
	@echo "  make test-all        V1 + V2 + V3"
	@echo "  make build-firmware  compile ESP32-S3 firmware in Docker"
	@echo "  make down            stop and remove containers/volumes"

up:
	$(COMPOSE) up -d gateway mosquitto

down:
	$(COMPOSE) --profile v1 --profile v2 --profile v3 --profile ml --profile firmware --profile ci down -v --remove-orphans

logs:
	$(COMPOSE) logs -f gateway

test-v1: $(REPORT_DIR)
	-$(COMPOSE) --profile v1 down -v --remove-orphans
	$(COMPOSE) --profile v1 up --build --abort-on-container-exit --exit-code-from test-v1 test-v1

test-v2: $(REPORT_DIR)
	-$(COMPOSE) --profile v2 down -v --remove-orphans
	$(COMPOSE) --profile v2 up --build --abort-on-container-exit --exit-code-from test-v2 test-v2

test-v3: $(REPORT_DIR)
	-$(COMPOSE) --profile v3 down -v --remove-orphans
	$(COMPOSE) --profile v3 up --build --abort-on-container-exit --exit-code-from test-v3 test-v3

test-ml:
	$(COMPOSE) --profile ml run --rm train-ml

test-all: test-v1 test-v2 test-v3

build-firmware:
	$(COMPOSE) --profile firmware build firmware-build

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)

clean:
	rm -rf reports data .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
