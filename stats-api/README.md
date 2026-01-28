# Stats API

Application for public usage statistics pages on arXiv.org.

## Docker setup (preferred)

1. Install [Docker](https://docs.docker.com/engine/install/)
1. [Set environment variables](#environment-variables)
1. [Set database connection](#database-connection)
1. From project root, run `make up-api`

## Native setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
1. Install [Python](https://www.python.org/downloads/) - see `pyproject.toml` for current version; use `uv` if you prefer
1. [Set environment variables](#environment-variables)
1. [Set database connection](#database-connection)
1. Run
   ```
   cd stats-api
   uv sync
   python stats_api/app.py
   ```

## Environment variables

Non-sensitive constants are declared in `stats_api.config`. The appropriate config is chosen based on the value of the `ENV` environment variable - `TEST`, `DEV`, or `PROD`.

Other variables may be set in a `.env` file or in your local environment (i.e. your shell or terminal session). If running locally with Docker, you must use an `.env` file. 

1. If using a `.env` file, create a file named `.env` in `stats-api/`
2. Set the following variables in that file or in your local environment: 
   ```
   ENV=DEV
   DB__DRIVERNAME=mysql+pymysql
   DB__USERNAME=readonly
   DB__PASSWORD={password}
   DB__HOST=0.0.0.0
   DB__PORT=3306
   DB__DATABASE=site_usage
   ```
   The password for the `stats-db` readonly user can be found in GCP Secret Manager.
   
   The host you set should point to your local database proxy. If running via Docker, set the host to
   `host.docker.internal`.
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
