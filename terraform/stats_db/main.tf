terraform {
  required_version = "~> 1.13"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.2"
    }
  }
  backend "gcs" {
    prefix = "stats-db"
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
    tier            = "db-perf-optimized-N-4" # 4 cores, 32 GB RAM
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

    database_flags {
      name  = "long_query_time"
      value = "60" # log queries that take longer than one minute
    }

    password_validation_policy {
      enable_password_policy      = true
      min_length                  = 20
      disallow_username_substring = true
    }
  }
  root_password = data.google_secret_manager_secret_version.db_root_pw.secret_data
  # deletion protection protects the instance at the GCP level
  deletion_protection = false
}

### database ###

resource "google_sql_database" "site_usage" {
  name      = "site_usage"
  instance  = google_sql_database_instance.stats_db.name
  charset   = "UTF8"
  collation = "utf8_general_ci"
  lifecycle {
    # prevent destroy protects the database only at the terraform level
    prevent_destroy = true
  }
}

### database user for migrations ###

data "google_secret_manager_secret_version" "db_user_pw" {
  secret  = "projects/${var.gcp_project_id}/secrets/${var.db_user_pw_secret_name}"
  version = "latest"
}

output "secret_db_user_pw" {
  value     = data.google_secret_manager_secret_version.db_user_pw
  sensitive = true # prevents exposure in logs and state file
}

resource "google_sql_user" "db_user" {
  name     = "siteusagemigrations"
  instance = google_sql_database_instance.stats_db.name
  password = data.google_secret_manager_secret_version.db_user_pw.secret_data

  password_policy {
    allowed_failed_attempts      = 5
    enable_failed_attempts_check = true # lock after too many failed login attempts
    enable_password_verification = true # require current password before changing it
  }
}
