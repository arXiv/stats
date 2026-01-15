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
from stats_api.utils import set_fastly_headers, get_arxiv_current_time, url_param_to_date

stats_ui = Blueprint("stats_ui", __name__, url_prefix="/")
stats_api = Blueprint("stats_api", __name__, url_prefix="/")


@stats_ui.route("stats/main", methods=["GET"])
@set_fastly_headers(keys=["stats", "main"])
def main() -> ResponseReturnValue:
    return make_response(render_template("main.html"), HTTPStatus.OK)


@stats_ui.route("stats/today", methods=["GET"])
@set_fastly_headers(keys=["stats", "today"])
def today() -> ResponseReturnValue:
    """assumes supplied date is arxiv local"""
    current_time = get_arxiv_current_time()
    date_ = request.args.get("date", current_time.date(), type=url_param_to_date)

    data = StatsService.get_today_page_data(current_time, date_)

    return make_response(
        render_template("today.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_ui.route("stats/monthly_submissions", methods=["GET"])
@set_fastly_headers(keys=["stats", "submissions", "monthly"])
def monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_submissions_page_data(get_arxiv_current_time().date())

    return make_response(
        render_template("monthly_submissions.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_ui.route("stats/monthly_downloads", methods=["GET"])
@set_fastly_headers(keys=["stats", "downloads", "monthly"])
def monthly_downloads() -> ResponseReturnValue:
    data = StatsService.get_downloads_page_data()

    return make_response(
        render_template("monthly_downloads.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_api.route("stats/get_hourly_requests", methods=["GET"])
@set_fastly_headers(keys=["stats", "requests", "hourly"])
def get_hourly_requests() -> ResponseReturnValue:
    """requires date arg, and assumes supplied date is arxiv local"""
    date_ = request.args.get("date", get_arxiv_current_time().date(), type=url_param_to_date)

    if not date_:
        raise BadRequest

    data = StatsService.get_hourly_requests(date_)

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response


@stats_api.route("stats/get_monthly_submissions", methods=["GET"])
@set_fastly_headers(keys=["stats", "submissions", "monthly"])
def get_monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_monthly_submissions()

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response


@stats_api.route("stats/get_monthly_downloads", methods=["GET"])
@set_fastly_headers(keys=["stats", "downloads", "monthly"])
def get_monthly_downloads() -> ResponseReturnValue:
    data = StatsService.get_monthly_downloads()

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response
