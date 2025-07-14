import os
from flask import Flask
from flask_cors import CORS
from config.app import config
from api import api
from routes.graph_routes import graph_routes


def create_app(app_config="development"):
    app = Flask(__name__)

    # Apply CORS
    CORS(app)

    # Register blueprints
    app.register_blueprint(graph_routes)  # Frontend routes
    app.register_blueprint(api, url_prefix="/api")  # Backend API

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
