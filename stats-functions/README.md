# Stats Functions

This library contains python scripts which collect arXiv site usage data and persist it to the `stats-db.site_usage` database.

All are cron jobs implemented as GCP Cloud Functions with pubsub triggers. Trigger messages are published by GCP Scheduler Jobs. All infrastructure as code can be found in `terraform/`.

### Aggregate Hourly Downloads

The aggregate hourly downloads job parses arXiv access logs saved to BigQuery, queries the main database for paper metadata, generates counts of downloads per category (with careful data validation), and then writes them to a database. It runs hourly.

### Hourly Edge Requests

The hourly edge requests job calls the Fastly Stats API, sums arXiv edge requests over all points of presence (POPs), and writes the sum to a database. It runs hourly.

## To deploy

Use the existing workflow(s) at `.github/workflows`.

1. Manually zip the source files for the job and copy that zip to `terraform/aggregate_hourly_downloads`:
    ```
    cd stats-functions/{function}/src
    zip -r src.zip .
    ```
1. Initialize the remote backend. The environment will be either `dev` or `prod`. Add the `-reconfigure` flag if needed.
    ```
    cd ../../../terraform/{function}
    terraform init --backend-config=”bucket={env}-arxiv-terraform-state”
    ```
1. Plan
    ```
    terraform plan --var-file={dev.tfvars or prod.tfvars} -var="commit_sha={commit hash}"
    ```
1. Apply
    ```
    terraform apply --var-file={dev.tfvars or prod.tfvars} -var="commit_sha={commit hash}"
    ```
    > Note: The commit hash input is used to version the source zip so that a change to source is detected and the resources are replaced.

## To run manually

This is only recommended for testing or in the case that a data patch is needed.

1. Create a python virtual environment and `pip install -r` both `requirements.txt` and `requirements-dev.txt`
1. Set your environment variables (see `terraform/*/envs/*.tfvars`)
1. Run the job with command line arguments
    ```
    python main.py {args}
    ```