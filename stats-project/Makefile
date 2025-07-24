.PHONY: up build-api run-api stop-api clean-api build-ui run-ui stop-ui clean-ui venv clean-venv

BE_IMAGE_NAME := arxiv-stats
BE_CONTAINER_NAME := arxiv-stats
BE_DOCKERFILE := Dockerfile.api
BE_BUILD_CONTEXT := .
BE_PORT := 8080

NODE_VERSION := $(shell cat frontend/.nvmrc | cut -c 2-)
FE_IMAGE_NAME := arxiv-stats-ui
FE_CONTAINER_NAME := arxiv-stats-ui
FE_DOCKERFILE := ./frontend/Dockerfile
FE_BUILD_CONTEXT := ./frontend
FE_PORT := 9000

up: stop-ui clean-ui stop-api clean-api build-api run-api build-ui run-ui

up-api: stop-api clean-api build-api run-api

up-ui: stop-ui clean-ui build-ui run-ui

build-api:
	docker build -f $(BE_DOCKERFILE) -t $(BE_IMAGE_NAME) $(BE_BUILD_CONTEXT) -D

run-api:
	docker run -d --name $(BE_CONTAINER_NAME) -p ${BE_PORT}:${BE_PORT} --env-file stats/.env $(BE_IMAGE_NAME) 

stop-api:
	docker stop $(BE_CONTAINER_NAME) || true

clean-api:
	docker rm $(BE_CONTAINER_NAME) || true
	docker rmi $(BE_IMAGE_NAME) || true

build-ui:
	docker build --build-arg NODE_VERSION=$(NODE_VERSION) -f $(FE_DOCKERFILE) -t $(FE_IMAGE_NAME) $(FE_BUILD_CONTEXT) --progress=plain

run-ui:
	docker run -d --name $(FE_CONTAINER_NAME) -p ${FE_PORT}:${FE_PORT} $(FE_IMAGE_NAME)

stop-ui:
	docker stop $(FE_CONTAINER_NAME) || true

clean-ui:
	docker rm $(FE_CONTAINER_NAME) || true
	docker rmi $(FE_IMAGE_NAME) || true

test-api:
	poetry run pytest