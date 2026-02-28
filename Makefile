.PHONY: install dev test lint format clean docker run

install:
	pip install .

dev:
	pip install ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing --tb=short

lint:
	ruff check app/ tests/

format:
	ruff format app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage test.db

docker:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"
