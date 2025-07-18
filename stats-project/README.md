# stats-project

Application for `/stats` pages on arxiv.org. `stats/` is the Flask backend, and `stats-ui/` is the React frontend.

## Requirements
#### To run stats natively:
1. [Python](https://www.python.org/downloads/) - see `pyproject.toml` for current version
2. [poetry](https://python-poetry.org/docs/#installation) - see `Dockerfile.api` for current version

#### To run stats-ui natively:
3. [Node](https://nodejs.org/en/download) - see `package.json` for current version

#### To run with Docker:
1. [Docker](https://docs.docker.com/engine/install/)

## Environment variables
1. Create a file named `.env` in `stats/`
2. Set the following variables
    ```
    DATABASE_URI={database}+{driver}://{username}:{password}@{host}:{port}/{db_name}
    ```
    You can find the database URI in GCP Secrets Manager.

## Database connection
1. Authenticate to GCP
    ```
    gcloud auth login
    ```
2. Run the proxy server locally
    ```
    cloud-sql-proxy --address {host} --port {port} {account}:{region}:{db_name}
    ```
    Your host address will be this network (`0.0.0.0`) or localhost (`127.0.0.1`). Choose any open port.

## Lifecycle commands

See `Makefile`. When developing, it is preferred to run both the backend and the frontend using Docker (rather than natively) as this mirrors production.

After completing setup, `make up` will build (or `make reup` will rebuild) and run the application.