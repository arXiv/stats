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

variable "read_db_user" {
  description = "Username for database paper metadata is being read from"
  type        = string
}

variable "read_db_pw_secret_name" {
  description = "Reference to password in Secret Manager for database paper metadata is being read from"
  type        = string
}

variable "read_db_host" {
  description = "Host for database paper metadata is being read from"
  type        = string
}

variable "read_db_port" {
  description = "Port for database paper metadata is being read from"
  type        = string
}

variable "write_db_user" {
  description = "Username for database aggregated data is being written to"
  type        = string
}

variable "write_db_pw_secret_name" {
  description = "Reference to password in Secret Manager for database aggregated data is being written to"
  type        = string
}

variable "write_db_host" {
  description = "Host for database aggregated data is being written to"
  type        = string
}

variable "write_db_port" {
  description = "Port for database aggregated data is being written to"
  type        = string
}