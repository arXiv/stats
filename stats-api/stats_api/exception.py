from flask import render_template
from werkzeug.exceptions import HTTPException


# 500 - use base template
def handle_non_http_exception(e):
    if isinstance(e, HTTPException):
        return e

    # return render_template("500_generic_exception.html", e=e), 500
    pass


# 400, 404, 405 - use browse template
def handle_http_exception(e):
    # return render_template("http_exception.html", e=e), e
    pass
