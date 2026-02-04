# Stats Functions package

The stats-function package contains shared configuration and utilities that can be used with any cloud functions.

# Stats Functions

Other directories contain python source code for production cloud functions which collect arXiv site usage data and persist it to the `stats-db.site_usage` database. See below for a description of each. All are cron jobs implemented as GCP Cloud Functions with pubsub triggers. Trigger messages are published by GCP Scheduler Jobs. All infrastructure as code can be found in `terraform/`.

All functions are idempotent.

## To deploy a function

To deploy any of the above cloud functions to a remote environment, use the existing workflow at `.github/workflows/deploy-function.yml`. Triggers for automated deployment can also be found in `.github/workflows/`.

## Aggregate Hourly Downloads

The aggregate hourly downloads job parses arXiv access logs saved to BigQuery, queries the main database for paper metadata, generates counts of downloads per category (with careful data validation), and then writes them to a database. It runs hourly.

### To run manually
```
gcloud pubsub topics publish stats-aggregate-hourly-downloads --message="" --attribute="hour=2025-12-1214"
```

## Hourly Edge Requests

The hourly edge requests job calls the Fastly Stats API, sums arXiv edge requests over all points of presence (POPs), and writes the sum to a database. It runs hourly.

### To run manually
```
gcloud pubsub topics publish stats-hourly-edge-requests --message="" --attribute="hour=2025-12-1214"
```

## Monthly Submissions

The monthly submissions job queries for the count of submissions in the past month and writes that sum to a database.

### To run manually
```
gcloud pubsub topics publish stats-monthly-downloads --message="" --attribute="month=2025-12-01"
```

## Monthly Submissions

The monthly downloads job queries for the count of downloads in the past month and writes that sum to a database.

### To run manually
```
gcloud pubsub topics publish stats-monthly-submissions --message="" --attribute="month=2025-12-01"
```
