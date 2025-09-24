## Aggregate hourly downloads job

The aggregate hourly downloads job parses arXiv access logs saved to BigQuery, queries the main database for paper metadata, generates counts of downloads per category (with careful data validation), and then writes them to a database for use.

This is a cron job implemented as a GCP Cloud Function with a pubsub trigger. Trigger messages are published by a GCP Scheduler Job.

Preferred deployment is with terraform - see `terraform/aggregate_hourly_downloads/`.

## To deploy with terraform

Currently this is deployed manually - in the future, this will be deployed via workflow.

1. Update variables - non-sensitive values can be updated in `.tfvars`(environment-specific); sensitive values should be in Secret Manager and referenced in the cloud function resource in `main.tf`.
1. Initialize the remote backend. The environment will be either `dev` or `prod`.
    ```
    terraform init -backend-config=”bucket={env}-arxiv-terraform-state”
    ```
1. Manually zip the source files for the job and copy that zip to `terraform/aggregate_hourly_downloads`:
    ```
    cd statsfunctions/aggregate_hourly_downloads/src
    zip src.zip main.py models.py entities.py requirements.txt
    ```
1. Apply
    ```
    terraform apply --var-file={dev.tfvars or prod.tfvars}
    ```
    > Note: The current terraform does not version the source zip object in the bucket, so subsequent `apply` executions may not update the cloud function resource (because terraform does not recognize that the source zip object has changed). To force an update, run `terraform apply --var-file={.tfvars} -replace google_cloudfunctions2_function.function`, then `terraform apply --var-file={.tfvars}` again (to update resources which reference the cloud function resource).

## To run manually with start and end dates

This is only recommended for testing (in dev) or in the case that the cron does not execute properly and a data patch is needed (in prod).

1. Create a python virtual environment and `pip install -r` both `requirements.txt` and `requirements-dev.txt`
1. Set your environment variables (see `.tfvars` and `variables.tf`)
1. If running in dev, ensure that sufficient log data is available in dev BigQuery at `_AllLogs`. If not, copy in a reasonable subset from production.
1. Run the job with a `start_time` and `end_time`:
    ```
    python main.py --start-time {YYYY-MM-DDHH} --end-time {YYYY-MM-DDHH}
    ```