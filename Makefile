.PHONY: up up-api up-ui build-api run-api stop-api clean-api build-ui run-ui stop-ui clean-ui test-api format-api

TARGET := runtime

BE_IMAGE_NAME := arxiv-stats
BE_CONTAINER_NAME := arxiv-stats
BE_DOCKERFILE := Dockerfile.api
BE_BUILD_CONTEXT := .
BE_PORT := 8080

FE_IMAGE_NAME := arxiv-stats-ui
FE_CONTAINER_NAME := arxiv-stats-ui
FE_DOCKERFILE := Dockerfile.ui
FE_BUILD_CONTEXT := .
FE_PORT := 3000

up: stop-ui clean-ui stop-api clean-api build-api run-api build-ui run-ui

up-api: stop-api clean-api build-api run-api

up-ui: stop-ui clean-ui build-ui run-ui

build-api:
	docker build $(BE_BUILD_CONTEXT) --build-arg PORT=$(BE_PORT) -f $(BE_DOCKERFILE) -t $(BE_IMAGE_NAME) --target $(TARGET) --progress plain

run-api:
	docker run -d --name $(BE_CONTAINER_NAME) -p ${BE_PORT}:${BE_PORT} --env-file stats/.env $(BE_IMAGE_NAME) 

stop-api:
	docker stop $(BE_CONTAINER_NAME) || true

clean-api:
	docker rm $(BE_CONTAINER_NAME) || true
	docker rmi $(BE_IMAGE_NAME) || true

build-ui:
	docker build $(FE_BUILD_CONTEXT) --build-arg PORT=$(FE_PORT) -f $(FE_DOCKERFILE) -t $(FE_IMAGE_NAME)  --progress plain

run-ui:
	docker run -d --name $(FE_CONTAINER_NAME) -p ${FE_PORT}:${FE_PORT} $(FE_IMAGE_NAME)

stop-ui:
	docker stop $(FE_CONTAINER_NAME) || true

clean-ui:
	docker rm $(FE_CONTAINER_NAME) || true
	docker rmi $(FE_IMAGE_NAME) || true

test-api:
	uv run pytest tests

format-api:
	ruff format stats