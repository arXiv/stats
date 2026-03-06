from werkzeug.exceptions import HTTPException, InternalServerError
from flask import render_template


def handle_non_http_exception(e):
    """
    handle non-HTTP (app-side) exceptions without leaking traceback
    """
    if isinstance(e, HTTPException):
        return e

    return render_template("generic_exception.html", error=InternalServerError()), 500


def handle_http_exception(e):
    return render_template("generic_exception.html", error=e), e.code
