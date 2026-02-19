variable "gcp_project_id" {
  description = "GCP Project ID corresponding to environment"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region for resource deployments"
  type        = string
}

variable "env" {
  description = "Deployment environment - DEV or PROD"
  type        = string
}

variable "commit_sha" {
  description = "Commit hash"
  type        = string
}

variable "write_db_drivername" {
  description = "Dialect+driver for the database connection"
  type        = string
}

variable "write_db_username" {
  description = "Username for the database data is written to"
  type        = string
}

variable "write_db_pw_secret_name" {
  description = "Reference to password in Secret Manager for the database data is written to"
  type        = string
}

variable "write_db_instance_name" {
  description = "Instance name for the database data is written to"
  type        = string
}

variable "write_db_database" {
  description = "Database name for the database data is written to"
  type        = string
}

variable "write_db_unix_socket" {
  description = "Full path to unix socket"
  type        = string
}

variable "slack_channel_id" {
  description = "Channel ID for slack notification channel resource"
  type        = string
}

