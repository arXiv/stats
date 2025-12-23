import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import URL

from stats_api.config.app import Database, TestConfig, DevConfig, ProdConfig
from stats_api.config.database import db
from stats_api.routes import stats_ui, stats_api
from stats_api.exception import handle_non_http_exception, handle_http_exception


config_map = {
    "TEST": TestConfig(DB=Database(drivername="sqlite", database=":memory:")),
    "DEV": DevConfig(),
    "PROD": ProdConfig(),
}


def create_app(environment: str) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map[environment])

    app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
        **app.config["DB"].model_dump()
    ).render_as_string()

    db.init_app(app)

    CORS(app)

    app.register_blueprint(stats_ui)
    app.register_blueprint(stats_api)

    # app.register_error_handler(Exception, handle_non_http_exception)
    # app.register_error_handler(Exception, handle_http_exception)

    return app


if __name__ == "__main__":
    app = create_app(os.getenv("ENV", "DEV"))

    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        use_reloader=False,
    )
