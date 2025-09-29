import os
from stats_api.config import TestConfig, DevConfig, ProdConfig
from stats_api.utils.database import db
from stats_api.utils.logging import configure_logging
from flask import Flask
from flask_cors import CORS
from stats_api.routes.api import api
from stats_api.routes.graph_routes import graph_routes

config_map = {
    "TEST": TestConfig,
    "DEV": DevConfig,
    "PROD": ProdConfig,
}


def create_app():
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(config_map[os.getenv("ENV", "TEST")])

    db.init_app(app)

    # Apply CORS
    CORS(app)

    # Register blueprints
    app.register_blueprint(graph_routes)
    app.register_blueprint(api, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
