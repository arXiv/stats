gcp_project_id    = "arxiv-production"
gcp_region        = "us-central1"
db_drivername     = "mysql+pymysql"
db_username       = "readonly"
db_pw_secret_name = "stats-db-readonly-pw"
db_database       = "site_usage"
db_unix_socket    = "/cloudsql/arxiv-production:us-central1:stats-db"
db_instance_name  = "arxiv-production:us-central1:stats-db"
slack_channel_id  = "1434512525946563886"

brand_static_base = "https://static.arxiv.org/static/design-system/latest/"

server_name = "arxiv.org"
base_server = "arxiv.org"
auth_server = "arxiv.org"
help_server = "info.arxiv.org"
debug       = false
