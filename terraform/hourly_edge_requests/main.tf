terraform {
  required_version = "~> 1.13"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.2"
    }
  }
  backend "gcs" {
    prefix = "stats-hourly-edge-requests"
  }
}

provider "google" {
  project = var.gcp_project_id # default inherited by all resources
  region  = var.gcp_region     # default inherited by all resources
}

### service account ###

resource "google_service_account" "account" {
  account_id   = "stats-requests"
  display_name = "Service account to deploy hourly-edge-requests cloud function"
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

resource "google_secret_manager_secret_iam_member" "fastly_token" {
  secret_id = "fastly_readonly_token"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
}

resource "google_secret_manager_secret_iam_member" "write_db" {
  secret_id = var.write_db_pw_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.account.email}"
}

### cloud function ###

resource "google_cloudfunctions2_function" "function" {
  name        = "stats-hourly-edge-requests" # name should use kebab-case so generated Cloud Run service name will be the same
  location    = var.gcp_region               # needs to be explicitly declared for Cloud Run
  description = "Cloud function to get hourly edge requests from Fastly API and persist to a database"

  build_config {
    runtime     = "python313"
    entry_point = "get_hourly_edge_requests"
    source {
      storage_source {
        bucket = google_storage_bucket.bucket.name
        object = google_storage_bucket_object.object.name
      }
    }
  }

  service_config {
    min_instance_count    = 1 # to reduce cold starts
    available_memory      = "2G"
    timeout_seconds       = 540 # 9 minutes is the maximum allowed
    ingress_settings      = "ALLOW_INTERNAL_ONLY"
    service_account_email = google_service_account.account.email
    environment_variables = {
      ENV               = var.env
      PROJECT           = var.gcp_project_id
      DB__USER          = var.write_db_user
      DB__INSTANCE_NAME = var.write_db_instance
      DB__DATABASE      = var.write_db_name
    }
    secret_environment_variables {
      key        = "FASTLY_API_TOKEN"
      project_id = var.gcp_project_id
      secret     = "fastly_readonly_token"
      version    = "latest"
    }
    secret_environment_variables {
      key        = "DB__PASSWORD"
      project_id = var.gcp_project_id
      secret     = var.write_db_pw_secret_name
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
  name                        = lower("${var.env}-stats-hourly-edge-requests") # prefixed with env because buckets must be globally unique
  location                    = "US"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "object" {
  name   = "stats-hourly-edge-requests-src-${var.commit_sha}.zip"
  bucket = google_storage_bucket.bucket.name
  source = "src.zip"
}

### scheduled pubsub ###

resource "google_pubsub_topic" "topic" {
  name = "stats-hourly-edge-requests"
}

resource "google_cloud_scheduler_job" "invoke_cloud_function" {
  name        = "invoke-stats-hourly-edge-requests"
  description = "Publish an hourly message to invoke the aggregate-hourly-downloads cloud function"
  schedule    = "5 * * * *" # every hour at five minutes past
  time_zone   = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.topic.id
    data       = base64encode("invoke")
  }
}

### alerting ###

resource "google_monitoring_alert_policy" "cloud_run_error_alert" {
  display_name = "${google_cloudfunctions2_function.function.name} logging errors"
  combiner     = "OR"
  severity     = "ERROR"

  conditions {
    display_name = "Cloud Run error log"
    condition_matched_log {
      filter = "resource.type=\"cloud_run_revision\" AND severity=(\"ERROR\" OR \"CRITICAL\" OR \"ALERT\" OR \"EMERGENCY\") AND resource.labels.service_name=\"${google_cloudfunctions2_function.function.name}\""
    }
  }

  alert_strategy {
    notification_rate_limit {
      period = "300s" # limit notifications to every 5 minutes
    }
  }

  notification_channels = [
    "projects/${var.gcp_project_id}/notificationChannels/${var.slack_channel_id}"
  ]

  documentation {
    content   = "Cloud Run service ${google_cloudfunctions2_function.function.name} has reported an error - see logs."
    mime_type = "text/markdown"
  }
}
