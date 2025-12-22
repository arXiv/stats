from datetime import date
from http import HTTPStatus
from werkzeug.exceptions import BadRequest
from flask import (
    Blueprint,
    render_template,
    make_response,
    request,
)
from flask.typing import ResponseReturnValue

from stats_api.service import StatsService
from stats_api.utils import get_arxiv_current_date

import logging

logger = logging.getLogger(__name__)


stats_ui = Blueprint("stats_ui", __name__, url_prefix="/")
stats_api = Blueprint("stats_api", __name__, url_prefix="/")


@stats_ui.route("stats/main", methods=["GET"])
def main() -> ResponseReturnValue:
    response = make_response(render_template("main.html"), HTTPStatus.OK)
    
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response


@stats_ui.route("stats/today", methods=["GET"])
def today() -> ResponseReturnValue:
    """assumes supplied date is arxiv local"""
    date_ = request.args.get("date", get_arxiv_current_date(), type=date)

    data = StatsService.get_today_page_data(date_)

    response = make_response(render_template("today.html", **data.model_dump()), HTTPStatus.OK)
    
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response


@stats_ui.route("stats/monthly_submissions", methods=["GET"])
def monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_submissions_page_data(get_arxiv_current_date())

    response = make_response(render_template("monthly_submissions.html", **data.model_dump()), HTTPStatus.OK)
    
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response


@stats_ui.route("stats/monthly_downloads", methods=["GET"])
def monthly_downloads() -> ResponseReturnValue:
    data = StatsService.get_downloads_page_data()
    
    response = make_response(render_template("monthly_downloads.html", **data.model_dump()), HTTPStatus.OK)
    
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response


@stats_api.route("stats/get_hourly_requests", methods=["GET"])
def get_hourly_requests() -> ResponseReturnValue:
    """requires date arg, and assumes supplied date is arxiv local"""
    date_ = request.args.get("date", None, type=date)

    if not date_:
        raise BadRequest

    data = StatsService.get_hourly_requests(date_)
    
    response = make_response(data, HTTPStatus.OK)
    
    response.headers["Content-Type"] = "text/csv"
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response



@stats_api.route("stats/get_monthly_submissions", methods=["GET"])
def get_monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_monthly_submissions()

    response = make_response(data, HTTPStatus.OK)
    
    response.headers["Content-Type"] = "text/csv"
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response


@stats_api.route("stats/get_monthly_downloads", methods=["GET"])
def get_monthly_downloads() -> ResponseReturnValue:
    data = StatsService.get_monthly_downloads()

    response = make_response(data, HTTPStatus.OK)
    
    response.headers["Content-Type"] = "text/csv"
    response.headers["Surrogate-Control"] = ""
    response.headers["Surrogate-Key"] = ""

    return response
