# stats-db
Use this package to manage changes to stats-db database, including site_usage. For more information, see [the Atlas docs](https://atlasgo.io/guides/orms/sqlalchemy).

The database user with appropriate permissions to execute migrations is terraformed - see `terraform/stats-db/main.tf`.

## Important notes

1. Do not commit data to this repo (schema changes only)
1. Do not make manual changes to `migrations/`

## Config
All configuration is in `atlas.hcl`. It includes two blocks - `data` points Atlas to our schema-as-code (ORM entities) and  `env` defines the environment for migrations. The `dev` attribute tells Atlas to run a docker container from a mysql base image to generate migration files (sql).

> IMPORTANT NOTE: Following the ORM paradigm, migrations are computed solely from changes to our schema-as-code - Atlas has no knowledge of the current state of the database when calculating migrations. Never make schema changes outside of migrations, and always check your changes against the database before deploying.

## Workflow
> NOTE: These steps should be executed via automated workflow; for now they are manual
1. Make changes to stats-entities
1. Sync your environment - this ensures all changes to stats-entities are found by Atlas
    ```
    cd stats-db
    uv sync
    ```
1. Generate a migration file based on your changes
    ```
    uv run atlas migrate diff --env sqlalchemy
    ```
1. Validate migrations against the dev database - this requires a mechanism to determine which set of migration files to analyze
    
    For manual checks, we provide a number of migration files
    ```
    atlas migrate lint --dev-url mysql://siteusagemigrations:{password}@{host}:{port}/site_usage --latest 1
    ```
    In an automated workflow, we will compare against main
    ```
    atlas migrate lint --dev-url mysql://siteusagemigrations:{password}@{host}:{port}/site_usage --git-base main
    ```
1. Deploy - this will make the changes and write migration metadata to the `atlas_schema_revisions` table
    ```
    atlas migrate apply --dry-run
    atlas migrate apply
    ```

If needed, revert a migration with `atlas migrate down` or restore the schema to its original state with `atlas schema clean`. See the Atlas docs for more information.
