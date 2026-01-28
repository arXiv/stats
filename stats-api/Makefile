.PHONY: up up-api build-api run-api stop-api clean-api

TARGET := runtime

BE_IMAGE_NAME := stats-api
BE_CONTAINER_NAME := stats-api
BE_DOCKERFILE := Dockerfile.api
BE_BUILD_CONTEXT := ./../
BE_PORT := 8080

up-api: stop-api clean-api build-api run-api

build-api:
	docker build $(BE_BUILD_CONTEXT) --build-arg PORT=$(BE_PORT) -f $(BE_DOCKERFILE) -t $(BE_IMAGE_NAME) --target $(TARGET) --progress plain

run-api:
	docker run -d --name $(BE_CONTAINER_NAME) -p ${BE_PORT}:${BE_PORT} --env-file .env $(BE_IMAGE_NAME) 

stop-api:
	docker stop $(BE_CONTAINER_NAME) || true

clean-api:
	docker rm $(BE_CONTAINER_NAME) || true
	docker rmi $(BE_IMAGE_NAME) || true
