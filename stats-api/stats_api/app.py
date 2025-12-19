import os
from flask import Flask
from flask_cors import CORS

from stats_api.logging import configure_logging
from stats_api.config import TestConfig, DevConfig, ProdConfig
from stats_api.database import db
from stats_api.routes import stats_ui, stats_api

config_map = {
    "TEST": TestConfig,
    "DEV": DevConfig,
    "PROD": ProdConfig,
}


def create_app(environment: str) -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(config_map[environment])

    db.init_app(app)

    CORS(app)

    app.register_blueprint(stats_ui)
    app.register_blueprint(stats_api)

    return app


if __name__ == "__main__":
    app = create_app(os.getenv("ENV", "DEV"))
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
