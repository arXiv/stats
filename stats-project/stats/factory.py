import os
from stats.config.app import config
from stats.utils.database import db
# from stats.utils.logging import configure_logging
from flask import Flask
from flask_cors import CORS
from stats.routes.api import api
from stats.routes.graph_routes import graph_routes


def create_app(app_config="development"):
    # configure_logging()
    # print("logging configured")

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    db.init_app(app)

    # Apply CORS
    CORS(app)

    # Register blueprints
    app.register_blueprint(graph_routes)
    app.register_blueprint(api, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
