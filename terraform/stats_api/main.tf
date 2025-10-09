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

# resource "google_service_account" "account" {
#   account_id   = "stats-api"
#   display_name = "Service account to deploy stats api cloud run instance"
# }

# resource "google_secret_manager_secret_iam_member" "read_db_secret_accessor" {
#   secret_id = var.read_db_secret_name
#   role      = "roles/secretmanager.secretAccessor"
#   member    = "serviceAccount:${google_service_account.account.email}"
# }

# resource "google_project_iam_member" "ar_writer" {
#   project = var.gcp_project_id
#   role    = "roles/artifactregistry.createOnPushWriter"
#   member  = "serviceAccount:${google_service_account.account.email}"
# }

# resource "google_project_iam_member" "cloud_run_admin" {
#   project = var.gcp_project_id
#   role    = "roles/run.admin"
#   member  = "serviceAccount:${google_service_account.account.email}"
# }

# resource "google_project_iam_member" "logs_writer" {
#   project = var.gcp_project_id
#   role    = "roles/logging.logWriter"
#   member  = "serviceAccount:${google_service_account.account.email}"
# }

# resource "google_project_iam_member" "service_account_user" {
#   project = var.gcp_project_id
#   role    = "roles/iam.serviceAccountUser"
#   member  = "serviceAccount:${google_service_account.account.email}"
# }

### cloud run instance ###

resource "google_cloud_run_v2_service" "stats_api" {
  name     = "stats-api"
  location = var.gcp_region

  deletion_protection = false

  template {
    containers {
      image = var.image_path
      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name = "DEV_DATABASE_URI"
        value_source {
          secret_key_ref {
            secret  = var.read_db_secret_name
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
        instances = [var.read_db_instance]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Get current project info for default service account
data "google_project" "current" {
  project_id = var.gcp_project_id
}

# Note: IAM permissions for the deployment service account are managed by arxiv-env script
# The deployment-sa@<project>.iam.gserviceaccount.com already has the necessary permissions:
# - roles/secretmanager.admin (includes secretAccessor and viewer)
# - roles/storage.objectViewer
# - roles/resourcemanager.projectIamAdmin
# - roles/serviceusage.serviceUsageAdmin
# - roles/run.developer

# IAM bindings for secrets (secrets are created by the workflow)
resource "google_secret_manager_secret_iam_binding" "secret_access" {
  for_each = { for secret in var.secrets_to_copy : secret.name => secret }
  project  = var.gcp_project_id
  secret_id = each.value.name
  role     = "roles/secretmanager.secretAccessor"
  members = var.service_account_email != "" ? [
    "serviceAccount:${var.service_account_email}",
  ] : [
    "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com",
  ]
}

# Enable Secret Manager API
resource "google_project_service" "secretmanager" {
  project = var.gcp_project_id
  service = "secretmanager.googleapis.com"
  
  disable_dependent_services = false
  disable_on_destroy        = false
}