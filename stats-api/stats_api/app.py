import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import URL

from stats_api.config.app import config_map
from stats_api.config.database import db
from stats_api.routes import stats_ui, stats_api


# from stats_api.exception import handle_non_http_exception, handle_http_exception


def create_app() -> Flask:
    app = Flask(__name__)

    environment = os.getenv("ENV", "TEST")
    app.config.from_object(config_map[environment]())

    app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
        **app.config["DB"].model_dump()
    ).render_as_string(hide_password=False)

    db.init_app(app)

    CORS(app)

    app.register_blueprint(stats_ui)
    app.register_blueprint(stats_api)

    # app.register_error_handler(Exception, handle_non_http_exception)
    # app.register_error_handler(Exception, handle_http_exception)

    return app
