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

variable "db_root_pw_secret_name" {
  description = "Reference to root database password in Secret Manager"
  type        = string
}

variable "db_user_pw_secret_name" {
  description = "Reference to database password in Secret Manager"
  type        = string
}
