terraform {
  required_version = "~> 1.13"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.2"
    }
  }
  backend "gcs" {
    prefix = "stats-stats-db"
  }
}

provider "google" {
  project = var.gcp_project_id # default inherited by all resources
  region  = var.gcp_region     # default inherited by all resources
}

### instance ###

data "google_secret_manager_secret_version" "db_root_pw" {
  secret  = "projects/${var.gcp_project_id}/secrets/${var.db_root_pw_secret_name}"
  version = "latest"
}

output "secret_db_root_pw" {
  value     = data.google_secret_manager_secret_version.db_root_pw
  sensitive = true # prevents exposure in logs and state file
}

resource "google_sql_database_instance" "stats_db" {
  database_version = "MYSQL_8_4"
  name             = "stats-db"
  settings {
    tier            = "db-custom-4-26" # 4 cores, 26 GB RAM (max allowed for 4 cores)
    edition         = "ENTERPRISE"
    disk_autoresize = true

    ip_configuration {
      # only allow connections encrypted with SSL/TLS and with valid client certificates
      # https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#ipconfiguration
      ssl_mode = "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"
    }

    backup_configuration {
      enabled            = true
      start_time         = "01:00"
      binary_log_enabled = true
    }

    password_validation_policy {
      enable_password_policy      = true
      min_length                  = 20
      disallow_username_substring = true
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
      query_string_length     = 2048 # max query length to capture
    }
  }
  root_password = data.google_secret_manager_secret_version.db_root_pw.secret_data
  # deletion protection protects the instance at the GCP level
  deletion_protection = true
}

### database ###

resource "google_sql_database" "site_usage" {
  name      = "site_usage"
  instance  = google_sql_database_instance.stats_db.name
  charset   = "utf8mb4"
  collation = "utf8mb4_general_ci"
  lifecycle {
    # prevent destroy protects the database only at the terraform level
    prevent_destroy = true
  }
}

### database user for migrations ###

data "google_secret_manager_secret_version" "db_mig_user_pw" {
  secret  = "projects/${var.gcp_project_id}/secrets/${var.db_mig_user_pw_secret_name}"
  version = "latest"
}

output "secret_db_mig_user_pw" {
  value     = data.google_secret_manager_secret_version.db_mig_user_pw
  sensitive = true # prevents exposure in logs and state file
}

resource "google_sql_user" "db_mig_user" {
  name     = "siteusagemigrations"
  instance = google_sql_database_instance.stats_db.name
  password = data.google_secret_manager_secret_version.db_mig_user_pw.secret_data

  password_policy {
    allowed_failed_attempts      = 5
    enable_failed_attempts_check = true # lock after too many failed login attempts
    enable_password_verification = true # require current password before changing it
  }
}

### database user for cron job connections ###

data "google_secret_manager_secret_version" "db_job_user_pw" {
  secret  = "projects/${var.gcp_project_id}/secrets/${var.db_job_user_pw_secret_name}"
  version = "latest"
}

output "secret_db_job_user_pw" {
  value     = data.google_secret_manager_secret_version.db_job_user_pw
  sensitive = true # prevents exposure in logs and state file
}

resource "google_sql_user" "db_job_user" {
  name     = "siteusagejobs"
  instance = google_sql_database_instance.stats_db.name
  password = data.google_secret_manager_secret_version.db_job_user_pw.secret_data

  password_policy {
    allowed_failed_attempts      = 5
    enable_failed_attempts_check = true # lock after too many failed login attempts
    enable_password_verification = true # require current password before changing it
  }
}

### database user for application connections ###

data "google_secret_manager_secret_version" "db_app_user_pw" {
  secret  = "projects/${var.gcp_project_id}/secrets/${var.db_app_user_pw_secret_name}"
  version = "latest"
}

output "secret_db_app_user_pw" {
  value     = data.google_secret_manager_secret_version.db_app_user_pw
  sensitive = true # prevents exposure in logs and state file
}

resource "google_sql_user" "db_app_user" {
  name     = "siteusagereadonly"
  instance = google_sql_database_instance.stats_db.name
  password = data.google_secret_manager_secret_version.db_app_user_pw.secret_data

  password_policy {
    allowed_failed_attempts      = 5
    enable_failed_attempts_check = true # lock after too many failed login attempts
    enable_password_verification = true # require current password before changing it
  }
}
