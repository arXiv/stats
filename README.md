# stats

Application for public usage statistics pages on arXiv.org. `stats/` contains the Flask backend and `stats-ui/` contains the React frontend.

## Docker setup (preferred)

1. Install [Docker](https://docs.docker.com/engine/install/)
2. [Set environment variables](#environment-variables)
3. [Set database connection](#database-connection)
4. Run `make up` to build and run both `stats` and `stats-ui`. See `Makefile` for additional lifecycle commands.

## Native setup

1. Install [Python](https://www.python.org/downloads/) - see `pyproject.toml` for current version
2. Install [poetry](https://python-poetry.org/docs/#installation) - see `Dockerfile.api` for current version
3. Install [Node](https://nodejs.org/en/download) - see `package.json` for current version
4. [Set environment variables](#environment-variables)
5. [Set database connection](#database-connection)
6. Install and run `stats`
   ```
   cd stats
   poetry install
   poetry run python factory.py
   ```
7. Install and run `stats-ui`
   ```
   cd ../stats-ui
   npm install
   npm run start
   ```

## Environment variables

NOTE: If you would like to use different ports and are running via Docker, make sure you also update the `FE_PORT` and `BE_PORT` in the `Makefile`.

Non-sensitive constants are declared in `stats.config`. The appropriate config is chosen based on the value of the `ENV` environment variable - `TEST`, `DEV`, or `PROD`.

Other variables may be set in a `.env` file or in your local environment (i.e. your shell or terminal session). If running locally with Docker, other variables must be set in an `.env` file. 

In remote environments, both non-sensitive and sensitive variables are declared in `cloudbuild.yaml` and injected at runtime.

1. If using a `.env` file, create a file named `.env` in `stats/`
2. Set the following variables in that file or in your local environment 
   ```
   ENV={environment}
   SQLALCHEMY_DATABASE_URI=postgresql+pg8000://{username}:{password}@{host}:{port}/latexmldb
   ```
   The database URI for the development `latexml-db` database can be found in GCP Secret Manager.
   
   The host you set in the URI should point to your local database proxy. If running via Docker, set the host to
   `host.docker.internal`.
3. Create a file named `.env` in `stats-ui/`
4. Set the following variables.
   ```
   PORT=9000
   ```

## Database connection

1. Authenticate to GCP (only needed once)
   ```
   gcloud auth login
   ```
2. Run the proxy server locally
   ```
   cloud-sql-proxy --address {host} --port {port} {account}:{region}:{db_name}
   ```
   Your host address will be this network (`0.0.0.0`) or localhost (`127.0.0.1`). Choose any open port.
