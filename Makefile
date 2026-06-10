IMAGE_TAG ?= v0.1.0-iot-ingestion

.PHONY: install lint build run compose-up compose-down logs test-compose

# Install Node dependencies for Prism/Spectral/Newman
install:
	pnpm install

# Lint OpenAPI contracts with Spectral
lint:
	pnpm exec spectral lint contracts/*.yaml

# Build Docker image for API only
build:
	docker build -t lab-5-hung981vpp-api:$(IMAGE_TAG) .

# Run API container standalone (not via compose)
run:
	docker run --rm --name fit4110-api-lab05 -p 8000:8000 --env-file .env.example lab-5-hung981vpp-api:$(IMAGE_TAG)

# Compose commands
compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

logs:
	docker compose logs -f

# Run Newman tests on compose stack
test-compose:
	pnpm run test:compose
