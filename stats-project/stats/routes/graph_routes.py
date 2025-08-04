"""
graph_routes.py

This module sets up the Flask Blueprint for rendering HTML templates.
It includes routes for rendering various statistics pages.

Routes:
    index():
        Renders the graph_routes statistics page.

    And other, assorted statistics rendering routes

Modules:
    flask: Provides the Flask web framework and template rendering.

Usage:
    Import this module and register the Blueprint with your Flask app to enable the HTML routes.
"""

from flask import Blueprint, render_template

graph_routes = Blueprint("graph_routes", __name__)


@graph_routes.route("/", methods=["GET"])
def index():
    return render_template("stats/main.html")


@graph_routes.route("/hourly_usage", methods=["GET"])
def render_hourly_usage():
    return render_template("stats/hourly_usage_rates.html")


@graph_routes.route("/monthly_downloads", methods=["GET"])
def render_monthly_downloads():
    return render_template("stats/monthly_downloads.html")


@graph_routes.route("/downloads_by_country", methods=["GET"])
def render_downloads_by_country():
    return render_template("stats/downloads_by_country.html")


@graph_routes.route("/downloads_by_category", methods=["GET"])
def render_downloads_by_category():
    return render_template("stats/downloads_by_category.html")


@graph_routes.route("/downloads_by_archive", methods=["GET"])
def render_downloads_by_archive():
    return render_template("stats/downloads_by_archive.html")


@graph_routes.route("/category_areagraph", methods=["GET"])
def render_category_areagraph():
    return render_template("stats/category_areagraph.html")


@graph_routes.route("/archive_areagraph", methods=["GET"])
def render_archive_areagraph():
    return render_template("stats/archive_areagraph.html")
