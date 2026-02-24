.PHONY: up-api stop-api clean-api build-api logs-api

up-api:
	docker compose -f docker-compose.local.yaml up -d

build-api:
	docker compose -f docker-compose.local.yaml build --progress plain

stop-api:
	docker compose -f docker-compose.local.yaml stop

clean-api:
	docker compose -f docker-compose.local.yaml down -v

logs-api:
	docker compose -f docker-compose.local.yaml logs -f