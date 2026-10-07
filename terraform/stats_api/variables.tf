variable "gcp_project_id" {
  description = "GCP Project ID corresponding to environment"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region for resource deployments"
  type        = string
}

variable "server_name" {
  description = "Host the app serves (Flask SERVER_NAME), e.g. arxiv.org"
  type        = string
}

variable "base_server" {
  description = "Host for links to the main site (home, search, create account)"
  type        = string
}

variable "auth_server" {
  description = "Host for login, logout and account links"
  type        = string
}

variable "help_server" {
  description = "Host for help and info links, e.g. info.arxiv.org"
  type        = string
}

variable "debug" {
  description = "Flask DEBUG"
  type        = bool
  default     = false
}

variable "image_path" {
  description = "Path to the container image in Artifact Registry"
  type        = string
}
variable "db_drivername" {
  description = "Dialect+driver for the database connection"
  type        = string
}

variable "db_username" {
  description = "Username for the database data is written to"
  type        = string
}

variable "db_pw_secret_name" {
  description = "Reference to password in Secret Manager for the database data is written to"
  type        = string
}

variable "db_database" {
  description = "Database name for the database data is written to"
  type        = string
}

variable "db_unix_socket" {
  description = "Full path to unix socket"
  type        = string
}

variable "db_instance_name" {
  description = "Instance name for the Cloud SQL instance"
  type        = string
}

variable "slack_channel_id" {
  description = "Channel ID for slack notification channel resource"
  type        = string
}

variable "brand_static_base" {
  description = "Design-system asset route the shared header and footer load (CSS, fonts, logos, chrome JS)"
  type        = string
}
