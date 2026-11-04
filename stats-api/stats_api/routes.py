from http import HTTPStatus

import dateutil.parser
from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import BadRequest

from stats_api.service import StatsService
from stats_api.utils import (
    get_arxiv_current_time,
    url_param_to_arxiv_datetime,
    url_param_to_date,
)

stats_ui = Blueprint("stats_ui", __name__, url_prefix="/")
stats_api = Blueprint("stats_api", __name__, url_prefix="/")


@stats_ui.route("stats/main", methods=["GET"])
def main() -> ResponseReturnValue:
    return make_response(render_template("main.html"), HTTPStatus.OK)


@stats_ui.route("stats/today", methods=["GET"])
def today() -> ResponseReturnValue:
    """assumes supplied date is arxiv local"""
    current_time = get_arxiv_current_time()
    date_ = request.args.get("date", current_time.date(), type=url_param_to_date)

    if date_ > current_time.date():
        raise BadRequest("The requested date is in the future.")

    data = StatsService.get_today_page_data(current_time, date_)

    return make_response(
        render_template("today.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_ui.route("stats/monthly_submissions", methods=["GET"])
def monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_submissions_page_data(get_arxiv_current_time().date())

    return make_response(
        render_template("monthly_submissions.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_ui.route("stats/monthly_downloads", methods=["GET"])
def monthly_downloads() -> ResponseReturnValue:
    data = StatsService.get_downloads_page_data()

    return make_response(
        render_template("monthly_downloads.html", **data.model_dump()), HTTPStatus.OK
    )


@stats_api.route("stats/get_hourly_requests", methods=["GET"])
def get_hourly_requests() -> ResponseReturnValue:
    """assumes supplied date is arxiv local"""
    today_ = get_arxiv_current_time().date()
    date = request.args.get("date", today_, type=url_param_to_date)

    if date > today_:
        raise BadRequest("The requested date is in the future.")

    data = StatsService.get_hourly_requests(date)

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response


@stats_api.route("stats/get_hourly", methods=["GET"])
def get_hourly() -> ResponseReturnValue:
    """browse's name for get_hourly_requests, kept so existing links and scripts work.
    browse read the date loosely (e.g. 2026-11-03 or 20261103), so this does too."""
    args = {}
    if "date" in request.args:
        try:
            args["date"] = dateutil.parser.parse(request.args["date"]).strftime(
                "%Y%m%d"
            )
        except (ValueError, OverflowError) as e:
            raise BadRequest("The requested date is not valid.") from e

    return redirect(
        url_for("stats_api.get_hourly_requests", **args), HTTPStatus.MOVED_PERMANENTLY
    )


@stats_api.route("stats/get_monthly_submissions", methods=["GET"])
def get_monthly_submissions() -> ResponseReturnValue:
    data = StatsService.get_monthly_submissions()

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response


@stats_api.route("stats/get_monthly_downloads", methods=["GET"])
def get_monthly_downloads() -> ResponseReturnValue:
    """latest_hour is optional and assumed arxiv local; without it, the newest hour
    stored is used (browse's version of this endpoint took no arguments)"""
    if "latest_hour" in request.args:
        try:
            latest_hour = url_param_to_arxiv_datetime(request.args["latest_hour"])
        except ValueError as e:
            raise BadRequest("latest_hour must be YYYYMMDDHH.") from e
    else:
        latest_hour = StatsService.get_latest_download_hour()

    data = StatsService.get_monthly_downloads(latest_hour)

    response = make_response(data, HTTPStatus.OK)
    response.headers["Content-Type"] = "text/csv"

    return response
