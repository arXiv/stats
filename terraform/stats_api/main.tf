terraform {
  required_version = "~> 1.13"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.2"
    }
  }
  backend "gcs" {
    prefix = "stats-stats-api"
  }
}

provider "google" {
  project = var.gcp_project_id # default inherited by all resources
  region  = var.gcp_region     # default inherited by all resources
}

### service account ###

resource "google_service_account" "account" {
  account_id   = "stats-api"
  display_name = "Service account to deploy stats api cloud run instance"
}

resource "google_secret_manager_secret_iam_member" "db_secret_accessor" {
  secret_id = var.db_pw_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "ar_writer" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.createOnPushWriter"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "cloud_run_admin" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "logs_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.account.email}"
}

resource "google_project_iam_member" "cloud_sql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.account.email}"
}

### cloud run instance ###

resource "google_cloud_run_v2_service" "stats_api" {
  name     = "stats-api"
  location = var.gcp_region

  template {
    service_account = google_service_account.account.email
    containers {
      image = var.image_path
      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name  = "DB__DRIVERNAME"
        value = var.db_drivername
      }
      env {
        name  = "DB__USERNAME"
        value = var.db_username
      }
      env {
        name  = "DB__DATABASE"
        value = var.db_database
      }
      env {
        name  = "DB__QUERY__UNIX_SOCKET"
        value = var.db_unix_socket
      }
      env {
        name = "DB__PASSWORD"
        value_source {
          secret_key_ref {
            secret  = var.db_pw_secret_name
            version = "latest"
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.db_instance_name]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

### alerting ###

resource "google_monitoring_alert_policy" "cloud_run_error_alert" {
  display_name = "${google_cloud_run_v2_service.stats_api.name} logging errors"
  combiner     = "OR"
  severity     = "ERROR"

  conditions {
    display_name = "Cloud Run error log"
    condition_matched_log {
      filter = "resource.type=\"cloud_run_revision\" AND severity=(\"ERROR\" OR \"CRITICAL\" OR \"ALERT\" OR \"EMERGENCY\") AND resource.labels.service_name=\"${google_cloud_run_v2_service.stats_api.name}\""
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
    content   = "Cloud Run service ${google_cloud_run_v2_service.stats_api.name} has reported an error - see logs."
    mime_type = "text/markdown"
  }
}
