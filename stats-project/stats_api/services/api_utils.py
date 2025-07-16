"""
api_utils.py

This module provides utility functions for querying and aggregating data from the database using SQLAlchemy.
It includes functions for time-based aggregation, querying models, and fetching specific data such as today's downloads.

Functions:
    get_time_group_column(model, time_group):
        Helper function to return the appropriate SQLAlchemy/MySQL extract functions for time-based aggregation.

    query_model(model_name, group_by_column, second_group_by_column=None, time_group=None):
        Query the specified model to aggregate data by a given column, optionally grouped by year, month, or day.

    query_global_sum(model_name, time_group):
        Queries the total sum of data aggregated by time group.

    query_todays_downloads():
        Queries for today's download statistics aggregated by hour.

Modules:
    os: Provides a way of using operating system dependent functionality.
    sqlalchemy: SQL toolkit and Object-Relational Mapping (ORM) library.
    dotenv: Loads environment variables from a .env file.
    models: Contains the SQLAlchemy models for the application.
    add_old_data: Contains functions to inject old data into the results.

Environment Variables:
    PROD_DB_URL: The database URL for the production environment.

SQLAlchemy Setup:
    engine: The SQLAlchemy engine created using the database URL.
    SessionFactory: The session factory created using the engine.
    Session: The scoped session created using the session factory.

Usage:
    Import the necessary functions from this module to query and aggregate data from the database.
    Ensure that the environment variables are properly set before using the functions.
"""

import os
from stats_api.utils.database import use_session
from sqlalchemy import func, extract, text
from models.models import get_model
from services.add_old_data import inject_old_data

def get_time_group_column(model, time_group):
    """
    Helper function to return the appropriate SQLAlchemy/MySQL extract functions for time-based aggregation.

    Args:
        model (SQLAlchemy Model): The SQLAlchemy model to extract time group columns from.
        time_group (str): The time group to extract ('year', 'month', 'day').

    Returns:
        list: A list of SQLAlchemy extract functions based on the specified time group.

    Raises:
        ValueError: If an invalid time group is provided.
    """
    if time_group == "year":
        return [extract("year", model.start_dttm)]
    elif time_group == "month":
        return [extract("year", model.start_dttm), extract("month", model.start_dttm)]
    elif time_group == "day":
        return [
            extract("year", model.start_dttm),
            extract("month", model.start_dttm),
            extract("day", model.start_dttm),
        ]
    else:
        raise ValueError(f"get_time_group_column recieved an invalid time group: {time_group}")

@use_session
def query_model(
    session, model_name, group_by_column, second_group_by_column=None, time_group=None
):
    """
    Query the specified model to aggregate data by a given column, optionally grouped by year, month, day, or hour.

    Args:
        model_name (str): The name of the model to query.
        group_by_column (str): The column to group by.
        second_group_by_column (str): An optional second column to further group by.
        time_group (str): Either 'month', 'year', 'day', or 'hour' to aggregate data by that period.

    Returns:
        final_result (list): A list of dicts, with keys corresponding to each given argument and their respective values based on said key.

    Raises:
        ValueError: If an incorrect model name or column is given.
    """
    print("stepped into query model.")
    model = get_model(model_name)
    if model is None:
        raise ValueError(f"Invalid model name: {model_name}")

    try:
        # Ensure the group_by column is valid
        group_by_attr = getattr(model, group_by_column, None)
        if not group_by_attr:
            raise ValueError(f"Query_model recieved an invalid group_by column: {group_by_column}")

        # Handle optional second grouping column
        second_group_by_attr = (
            getattr(model, second_group_by_column, None)
            if second_group_by_column
            else None
        )

        # Base columns and group by settings
        columns = [group_by_attr, func.sum(model.primary_count).label("data")]
        group_by_columns = [group_by_attr]

        # Add second group by column if present
        if second_group_by_attr:
            columns.append(second_group_by_attr)
            group_by_columns.append(second_group_by_attr)

        # Handle time aggregation by extraction specified time group
        if time_group:
            time_extracts = get_time_group_column(model, time_group)
            columns.extend(time_extracts)
            group_by_columns.extend(time_extracts)

        # Construct and execute query
        query = session.query(*columns).group_by(*group_by_columns)

        result = query.all()

        # Format results
        final_result = []
        for row in result:
            data = {group_by_column: row[0], "data": row[1]}
            index = 2

            # capitalize country names
            if group_by_column == "country":
                data[group_by_column] = data[group_by_column].title()

            # increase index if a second_group_by_column is present
            if second_group_by_column:
                data[second_group_by_column] = row[index]
                index += 1

            # fill in the rest of the date
            if time_group:
                time_values = row[index:]
                if time_group == "year":
                    data["time_group"] = f"{time_values[0]}-01-01"
                elif time_group == "month":
                    data["time_group"] = f"{time_values[0]}-{time_values[1]:02d}-01"
                elif time_group == "day":
                    data["time_group"] = (
                        f"{time_values[0]}-{time_values[1]:02d}-{time_values[2]:02d}"
                    )

            final_result.append(data)

        return final_result

    except Exception as e:
        raise

@use_session
def query_global_sum(session, model_name, time_group):
    """
    Queries the total sum of data aggregated by time group.

    Args:
        model_name (str): The name of the model to query.
        time_group (str): The time group to aggregate by ('year', 'month', 'day').

    Returns:
        final_result (list): A list of dicts, with keys 'total_sum' and 'time_group' representing the aggregated data.

    Raises:
        ValueError: If an incorrect model name or time value is given.
    """
    model = get_model(model_name)
    if model is None:
        raise ValueError(f"Invalid model name: {model_name}")

    try:
        # Initialize the database query results
        columns = [func.sum(model.primary_count).label("total_sum")]
        group_by_columns = get_time_group_column(model, time_group)
        columns.extend(group_by_columns)

        # Create the query to fetch database data
        query = session.query(*columns).group_by(*group_by_columns)

        # Execute the query and fetch results
        result = query.all()
        final_result = []

        # Process database results
        for row in result:
            data = {"total_sum": row[0]}
            time_values = row[1:]
            if time_group:
                if time_group == "year":
                    time_group_value = str(time_values[0])
                elif time_group == "month":
                    time_group_value = f"{time_values[0]}-{int(time_values[1]):02d}-01"
                elif time_group == "day":
                    time_group_value = f"{time_values[0]}-{int(time_values[1]):02d}-{int(time_values[2]):02d}"
 

            data["time_group"] = time_group_value
            final_result.append(data)

        # inject old data if required
        # delete me if our old data is ever imported to the new DB.
        if time_group == "month":
            final_result = inject_old_data(final_result, "monthly")
        elif time_group == "year":
            final_result = inject_old_data(final_result, "yearly")
        return final_result

    except Exception as e:
        raise


""" def query_todays_downloads():
    Queries for today's download statistics aggregated by hour.

    Returns:
        formatted_result (list): A list of dicts, with keys 'hour' and 'total_primary' representing the aggregated data.

    Raises:
        Exception: If there is an error in executing the query.
    session = Session()
    try:
        # Open a raw connection and execute a canned query.
        query = text(
            SELECT 
                EXTRACT(HOUR FROM start_dttm) AS hour,
                SUM(primary_count) AS total_primary_count
            FROM 
                hourly_download_data
            WHERE 
                DATE(start_dttm) = CURRENT_DATE
            GROUP BY 
                EXTRACT(HOUR FROM start_dttm)
            ORDER BY 
                hour;
        )
        result = session.execute(query).fetchall()

        # Format results into JSON
        formatted_result = [{"hour": row[0], "total_primary": row[1]} for row in result]

        return formatted_result

    except Exception as e:
        raise

    finally:
        session.close() """

@use_session
def query_todays_downloads(session, timezone='UTC'):
    """
    Queries for today's download statistics aggregated by hour in the specified timezone.

    Args:
        timezone (str): The IANA timezone string, e.g., 'America/New_York'. Defaults to UTC.

    Returns:
        formatted_result (list): A list of dicts, with keys 'hour' and 'total_primary'.
    """
    try:
        query = text(f"""
            SELECT 
                EXTRACT(HOUR FROM start_dttm AT TIME ZONE 'UTC' AT TIME ZONE :tz) AS local_hour,
                SUM(primary_count) AS total_primary_count
            FROM 
                hourly_download_data
            WHERE 
                start_dttm AT TIME ZONE 'UTC' AT TIME ZONE :tz >= date_trunc('day', now() AT TIME ZONE :tz)
                AND start_dttm AT TIME ZONE 'UTC' AT TIME ZONE :tz < date_trunc('day', now() AT TIME ZONE :tz) + interval '1 day'
            GROUP BY 
                local_hour
            ORDER BY 
                local_hour;
        """)

        result = session.execute(query, {"tz": timezone}).fetchall()
        formatted_result = [{"hour": int(row[0]), "total_primary": row[1]} for row in result]
        return formatted_result

    except Exception as e:
        raise

