from logging.config import dictConfig


def setup_logging():
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                },
                "gunicorn": {
                    "format": "%(message)s",  # gunicorn adds its own timestamps
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                },
                "gunicorn.error": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "formatter": "default",
                },
            },
            "loggers": {
                "flask": {
                    "handlers": [
                        "gunicorn.error"
                    ],  # route flask logs to gunicorn's error stream
                    "level": "INFO",
                    "propagate": False,
                },
                "stats_api": {
                    "handlers": ["gunicorn.error"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {"level": "WARNING", "handlers": ["gunicorn.error"]},
        }
    )
