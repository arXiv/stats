# stats-db
Use this package to manage changes to stats-db databases, including `site_usage`. For more information, see [the Atlas docs](https://atlasgo.io/guides/orms/sqlalchemy).

The database user with appropriate permissions to execute migrations is terraformed - see `terraform/stats-db/main.tf`.

## Important notes

1. Do not use migrations to change the state of data! Migrations should ONLY make schema changes - all data changes should be made manually
1. All `stats-db` schema changes should be made via Atlas
1. Do not make manual changes to any files in `migrations/`

## Config
All configuration is in `atlas.hcl`. It includes two blocks - `data` points Atlas to our schema-as-code (ORM entities) and  `env` defines the environment for migrations. The `dev` attribute tells Atlas to run a docker container from a mysql base image to generate migration files (sql).

> IMPORTANT NOTE: Following the ORM paradigm, migrations are computed solely from changes to our schema-as-code - Atlas has no knowledge of the current state of the database when calculating migrations. Never make schema changes outside of migrations, and always check your changes against the database before deploying.

## Workflow
> NOTE: These steps should be executed via automated workflow; for now they are manual
1. Make changes to `stats-entities`
1. Sync your environment - this ensures all changes to stats-entities are found by Atlas
    ```
    cd stats-db
    uv sync
    ```
1. Generate a migration file based on your changes
    ```
    atlas migrate diff --env sqlalchemy
    ```
1. Dry-run - view SQL to be applied before applying it
    ```
    atlas migrate apply --url mysql://admin:{password}@{host}:{port}/site_usage --dry-run
    ```
1. Deploy - apply changes and write migration metadata to the `atlas_schema_revisions` table
    ```
    atlas migrate apply --url mysql://admin:{password}@{host}:{port}/site_usage
    ```
1. After deploying to a local or development database to test, deploy to production

## Rollbacks
> NOTE: Not all migrations can be rolled back easily! Take precaution before applying, and consider a roll forward with a new migration
1. Checkout the branch which contains the migrations you'd like to roll back
1. Dry-run - view the checks and SQL to be applied before rolling back
    ```
    atlas migrate down --env sqlalchemy --url mysql://admin:{password}@{host}:{port}/site_usage --to-version {version to roll back to} --dry-run
    ```
1. Rollback - run checks and roll back to the migration specified
    ```
    atlas migrate down --env sqlalchemy --url mysql://admin:{password}@{host}:{port}/site_usage --to-version {version to roll back to}
    ```
1. Check the `atlas_schema_revisions` table in the db - references to the rolled back migrations should be removed
1. Safely remove the migration
    ```
    atlas migrate rm --env sqlalchemy {version to remove}
    ```
1. Revert changes to `stats-entities` (ORM code), or simply delete the branch, if not merged to main

