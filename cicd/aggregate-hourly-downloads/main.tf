provider "google" {
  project = var.gcp_project_id # default inherited by all resources
  region  = var.gcp_region     # default inherited by all resources
}

### service account ###

resource "google_service_account" "account" {
  account_id   = "stats-downloads"
  display_name = "Service account to deploy aggregate-hourly-downloads cloud function"
}

resource "google_cloudfunctions2_function_iam_member" "invoker" {
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.account.email}"
}

resource "google_cloud_run_service_iam_member" "cloud_run_invoker" {
  service = google_cloudfunctions2_function.function.name
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_secret_manager_secret_iam_member" "read_db" {
  secret_id = var.read_db_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
}

resource "google_secret_manager_secret_iam_member" "write_db" {
  secret_id = var.write_db_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "bq_jobs_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_bigquery_dataset_iam_member" "viewer" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.account.email}"
}

### existing bigquery table ###

import {
  to = google_bigquery_dataset.dataset
  id = "arxiv-development.arxiv_logs"
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id = "arxiv-development.arxiv_logs"

  lifecycle {
    prevent_destroy = true
  }
}

### cloud function ###

resource "google_cloudfunctions2_function" "function" {
  name        = "stats-aggregate-hourly-downloads" # name should use kebab-case so generated Cloud Run service name will be the same
  location    = var.gcp_region                     # needs to be explicitly declared for Cloud Run
  description = "Cloud function to parse download data from logs and persist to a database"

  build_config {
    runtime     = "python311"
    entry_point = "aggregate_hourly_downloads"
    source {
      storage_source {
        bucket = google_storage_bucket.bucket.name
        object = google_storage_bucket_object.object.name
      }
    }
  }

  service_config {
    min_instance_count    = 1
    available_memory      = "2G"
    timeout_seconds       = 60
    ingress_settings      = "ALLOW_INTERNAL_ONLY"
    service_account_email = google_service_account.account.email
    environment_variables = {
      ENV       = var.env
      LOG_LEVEL = var.log_level
    }
    secret_environment_variables {
      key        = "CLASSIC_DB_URI"
      project_id = var.gcp_project_id
      secret     = var.read_db_secret_name # wouldn't have to pass this in as a var if we had consistent secret naming across envs
      version    = "latest"
    }
    secret_environment_variables {
      key        = "WRITE_TABLE"
      project_id = var.gcp_project_id
      secret     = var.write_db_secret_name
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region = "us-central1"
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.topic.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}

resource "google_storage_bucket" "bucket" {
  name                        = "dev-stats-aggregate-hourly-downloads" # prefixed with env because buckets must be globally unique
  location                    = "US"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "object" {
  name   = "aggregate-hourly-downloads-src.zip"
  bucket = google_storage_bucket.bucket.name
  source = "src.zip"
}

### scheduled pubsub ###

resource "google_pubsub_topic" "topic" {
  name = "stats-aggregate-hourly-downloads"
}

resource "google_cloud_scheduler_job" "invoke_cloud_function" {
  name        = "invoke-stats-aggregate-hourly-downloads"
  description = "Publish an hourly message to invoke the aggregate-hourly-downloads cloud function"
  schedule    = "1 * * * *" # every hour at one minute past
  time_zone   = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.topic.id
    data       = base64encode("invoke")
  }
}
