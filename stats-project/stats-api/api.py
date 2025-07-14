"""
api.py

This module sets up the Flask Blueprint for the API and defines the routes for querying and aggregating data.
It includes endpoints for fetching aggregated data, global sums, and today's download statistics.

Functions:
    validate_args(model_name, group_by_column, second_group_by_column=None, time_group=None):
        Helper function to validate model name, column names, and time group.

    get_data():
        API endpoint to fetch aggregated data.

    get_global_sum():
        API endpoint to fetch the global sum of data aggregated by time unit.

    get_todays_downloads():
        API endpoint to fetch today's download statistics aggregated by hour.

Modules:
    flask: Provides the Flask web framework.
    flask_cors: Provides Cross-Origin Resource Sharing (CORS) support for Flask.
    services.api_utils: Contains utility functions for querying and aggregating data.
    models: Contains the SQLAlchemy models for the application.

Usage:
    Import this module and register the Blueprint with your Flask app to enable the API endpoints.
"""

from flask import Blueprint, jsonify, request
from flask_cors import CORS
from services.api_utils import query_model, query_global_sum, query_todays_downloads
from models import get_model

# Setup Flask Blueprint and CORS
api = Blueprint("api", __name__)
CORS(api, resources={r"/*": {"origins": "*"}})


def validate_column(model, column_name):
    """Helper function to validate a column name exists on a model."""
    if not hasattr(model, column_name):
        raise ValueError(f"Invalid column name: {column_name}")


@api.route("/get_data", methods=["GET"])
def get_data():
    """API endpoint to fetch aggregated data."""
    model_name = request.args.get("model")
    group_by_column = request.args.get("group_by")
    second_group_by_column = request.args.get("second_group_by")
    time_group = request.args.get("time_group")

    # check base parameters
    if not model_name or not group_by_column:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        model = get_model(model_name)
        if model is None:
            raise ValueError(f"Invalid model name: {model_name}")

        # Validate our arguments
        validate_column(model, group_by_column)
        if second_group_by_column:
            validate_column(model, second_group_by_column)
        if time_group and time_group not in ("year", "month", "day"):
            return (
                jsonify({"error": "Invalid time_group, use year, month, or day"}),
                400,
            )

        # attempt to query the model using our given arguments and return in json format for the frontend
        data = query_model(
            model_name, group_by_column, second_group_by_column, time_group
        )
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@api.route("/get_global_sum", methods=["GET"])
def get_global_sum():
    """API endpoint to fetch the global sum of data aggregated by time unit."""
    model_name = request.args.get("model")
    time_group = request.args.get("time_group")

    if not model_name or not time_group:
        return jsonify({"error": "Missing required parameters"}), 400

    if time_group and time_group not in ("year", "month", "day", "hour"):
        return jsonify({"error": "Invalid time_group, use year, month, or day"}), 400

    try:
        model = get_model(model_name)
        if model is None:
            raise ValueError(f"Invalid model name: {model_name}")

        data = query_global_sum(model_name, time_group)
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@api.route("/get_todays_downloads", methods=["GET"])
def get_todays_downloads():
    """API endpoint to fetch today's download statistics aggregated by hour, optionally in a specified timezone. Defaults to UTC."""
    try:
        timezone = request.args.get("timezone", "UTC")

        # Only allow known safe timezones to prevent SQL injection or invalid queries
        # TODO: Use more universal timezones / add more. 
        allowed_timezones = {
            "UTC",
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Kolkata",
            "Australia/Sydney"
        }

        if timezone not in allowed_timezones:
            return jsonify({"error": f"Invalid timezone '{timezone}'"}), 400

        data = query_todays_downloads(timezone)
        return jsonify(data)

    except Exception:
        return jsonify({"error": "Internal server error"}), 500
