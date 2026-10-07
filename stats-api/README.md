# Stats API

Application for public usage statistics pages on arXiv.org.

## Docker setup (preferred)

1. Install [Docker](https://docs.docker.com/engine/install/)
1. Export the following environment variables
   ```
   export DB__PASSWORD={password}  # the stats-db readonly password, in GCP Secret Manager
   export LOCAL_PATH_TO_CREDS={path to a GCP service account key json}
   ```
1. Build and run
   ```
   cd stats-api
   make up-api
   ```

## Native setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Install [Python](https://www.python.org/downloads/) - see `pyproject.toml` for current version; use `uv` if you prefer
1. [Set environment variables](#environment-variables)
1. [Set database connection](#database-connection)
1. Run
   ```
   cd stats-api
   uv sync
   uv run flask --app stats_api.app:create_app run --port 8080
   ```

## Development

`uv sync` installs the dev dependencies (pytest, ruff, ty) alongside the app's; the Docker
image installs only the app's (`uv sync --no-dev`).

```
cd stats-api
make test    # pytest
make lint    # ruff check
make type    # ty check
make format  # ruff format
```

## Environment variables

For a native setup, set environment variables in a `.env` file or in your local environment.

1. If using a `.env` file, create a file named `.env` in `stats-api/`
2. Set the following variables in that file or in your local environment: 
   ```
   SERVER_NAME=dev.arxiv.org
   BASE_SERVER=dev.arxiv.org
   AUTH_SERVER=dev.arxiv.org
   HELP_SERVER=info.dev.arxiv.org
   DEBUG=true
   BRAND_STATIC_BASE=https://static.dev.arxiv.org/static/design-system/latest/
   TOTAL_DELETED_PAPERS=156
   DB__DRIVERNAME=mysql+pymysql
   DB__USERNAME=readonly
   DB__PASSWORD={password}
   DB__HOST=0.0.0.0
   DB__PORT=3306
   DB__DATABASE=site_usage
   ```
   The password for the `stats-db` readonly user can be found in GCP Secret Manager.
   
   The host you set should point to your local database proxy.
1. For a socket connection to the database, unset the host and port, and set the socket instead:
    ```
    DB__QUERY__UNIX_SOCKET=/cloudsql/arxiv-development:us-central1:stats-db
    ```

## Database connection

1. Authenticate to GCP (only needed once)
   ```
   gcloud auth login
   ```
2. Run the proxy server locally
   ```
   cloud-sql-proxy arxiv-development:us-central1:stats-db -a 0.0.0.0 -p 3306
   ```
   Your host address will be this network (`0.0.0.0`) or localhost (`127.0.0.1`). Choose any open port.
