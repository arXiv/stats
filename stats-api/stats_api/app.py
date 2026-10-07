import arxiv_brand
from flask import Flask
from flask_cors import CORS
from sqlalchemy import URL
from werkzeug.exceptions import HTTPException

from stats_api.cache import set_fastly_headers
from stats_api.config.app import Config
from stats_api.config.database import db
from stats_api.exception import handle_http_exception, handle_non_http_exception
from stats_api.routes import stats_api, stats_ui


def create_app(config: Config | None = None) -> Flask:
    # Under /stats so arxiv.org's /stats/* route reaches these files too; /static/* belongs
    # to other apps there.
    app = Flask(__name__, static_url_path="/stats/static")

    app.config.from_object(config or Config())

    app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(**app.config["DB"].model_dump())

    db.init_app(app)

    CORS(app)

    arxiv_brand.init_app(app)

    app.register_blueprint(stats_ui)
    app.register_blueprint(stats_api)

    app.after_request(set_fastly_headers)

    app.register_error_handler(Exception, handle_non_http_exception)
    app.register_error_handler(HTTPException, handle_http_exception)

    return app
