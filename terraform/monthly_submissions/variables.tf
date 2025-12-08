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

variable "read_db_user" {
  description = "Username for database paper metadata is read from"
  type        = string
}

variable "read_db_pw_secret_name" {
  description = "Reference to password in Secret Manager for database paper metadata is read from"
  type        = string
}

variable "read_db_instance" {
  description = "Instance name for database paper metadata is read from"
  type        = string
}

variable "read_db_name" {
  description = "Database name for database paper metadata is read from"
  type        = string
}

variable "write_db_user" {
  description = "Username for database aggregated data is written to"
  type        = string
}

variable "write_db_pw_secret_name" {
  description = "Reference to password in Secret Manager for database aggregated data is written to"
  type        = string
}

variable "write_db_instance" {
  description = "Instance name for database aggregated data is written to"
  type        = string
}

variable "write_db_name" {
  description = "Database name for database aggregated data is written to"
  type        = string
}

variable "slack_channel_id" {
  description = "Channel ID for slack notification channel resource"
  type        = string
}