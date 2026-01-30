variable "gcp_project_id" {
  description = "GCP Project ID corresponding to environment"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region for resource deployments"
  type        = string
}

variable "env" {
  description = "Deployment environment"
  type        = string
}

variable "commit_sha" {
  description = "Commit hash"
  type        = string
}

variable "db_user" {
  description = "Database username"
  type        = string
}

variable "db_pw_secret_name" {
  description = "Reference to database password in Secret Manager"
  type        = string
}

variable "db_instance" {
  description = "Database instance name"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "slack_channel_id" {
  description = "Channel ID for slack notification channel resource"
  type        = string
}