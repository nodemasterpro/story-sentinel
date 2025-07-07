# Story Sentinel Makefile

.PHONY: help build run stop clean docker-build docker-run docker-stop test lint

# Default target
help:
	@echo "Story Sentinel Development Commands"
	@echo "================================="
	@echo "Docker commands:"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run with Docker (requires .env file)"
	@echo "  make docker-stop     Stop Docker container"
	@echo "  make docker-clean    Remove container and image"
	@echo ""
	@echo "Development commands:"
	@echo "  make install         Install in development mode"
	@echo "  make test            Run tests"
	@echo "  make lint            Run linting"
	@echo "  make clean           Clean build artifacts"

# Docker commands
docker-build:
	docker build -t story-sentinel:latest .

docker-run:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Copy .env.docker to .env and configure it."; \
		exit 1; \
	fi
	docker run -d --name story-sentinel \
		--env-file .env \
		-p 8080:8080 \
		-v sentinel-data:/data \
		--restart unless-stopped \
		story-sentinel:latest

docker-stop:
	docker stop story-sentinel || true
	docker rm story-sentinel || true

docker-clean: docker-stop
	docker rmi story-sentinel:latest || true
	docker volume rm sentinel-data || true

# Development commands
install:
	pip install -e .
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

lint:
	flake8 sentinel/
	black --check sentinel/

format:
	black sentinel/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Quick setup for new users
setup-env:
	@if [ ! -f .env ]; then \
		cp .env.docker .env; \
		echo "Created .env file from template. Please edit it with your configuration."; \
	else \
		echo ".env file already exists."; \
	fi

# Health check
health:
	@curl -f http://localhost:8080/health || echo "Service is not responding"