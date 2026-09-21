.PHONY: up-api stop-api clean-api build-api logs-api test lint type format

up-api:
	docker compose -f docker-compose.local.yaml up -d --build

build-api:
	docker compose -f docker-compose.local.yaml build --progress plain

stop-api:
	docker compose -f docker-compose.local.yaml stop

clean-api:
	docker compose -f docker-compose.local.yaml down -v

logs-api:
	docker compose -f docker-compose.local.yaml logs -f

test:
	uv run pytest

lint:
	uv run ruff check

type:
	uv run ty check

format:
	uv run ruff format