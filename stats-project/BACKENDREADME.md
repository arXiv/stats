# Student statistics dashboard project backend

## Overview

This folder intends to hold the core functionalities behind the statistics page on Arxiv, as an independent package as opposed to its eventual implementation to Arxiv Browse and as a standalone Cloud Run.

This document is to be updated as it nears production-ready status.

  

## Prerequisites

This project is reliant on the following libraries to function:

- Flask 3.0.3
- Flask-Cors 4.0.1
- python-dotenv 0.21.0
- SQLAlchemy 1.4.53
- pymysql 1.1.0
- mysqlclient 2.2.4

## Relevant Files

- api.py: A Flask Blueprint providing RESTful API endpoints for querying our data.
- api_util.py: Provides the utility functions for connecting, querying, and aggregating data from our databases using SQLAlchemy, and packaging this data into JSON format. 
- - add_old_data.py: When applicable, injects our old, less detailed data into sheets where it can fit in (primarily yearly and monthly download numbers.).

## Configure the Database URI as an environment variable

To ensure the app and API are able to connect to the database correctly, create a `.env` file within the `backend` folder, with a variable named `DATABASE_URI`, a mySQL or PostGres URI to your database. If you are connecting to a cloudSQL database, be sure to run the proxy. If you intend to run this project within a docker container, ensure the URI uses a TCP connection, and if the URI needs to connect to a service on the host machine, replace part of the IP address (but not the port!) to host.docker.internal.

  

## Run the Flask Application with Python

In a command line terminal, navigate to 'stats-project/frontend', and run the command

`python factory.py.`

This should start the app which should be accessible on http://127.0.0.1:8080/ in your browser.

  

## Run with Docker

There is a dockerfile provided in the root of the project. To build an image from it, navigate to the backend folder within a command line terminal and build it using commands

```docker build -t arxiv-stats-api-image .``` and

```docker run -p 8080:8080 arxiv-stats-api-image```

This should start the app which should be accessible on http://127.0.0.1:8080/ in your browser.

  
  

## Frontend

To be replaced with a react frontend within its own folder, for now there is a development "frontend" that serves some demo graphs within `stats-api/templates`:

- archive_areagraph.html
- category_areagraph.html
- downloads_by_archive.html
- downloads_by_category.html
- hourly_usage_rates.html
- monthly_downloads.html

  

# API Endpoints/Parameters

The API itself is intended to aggregate Primary downloads of papers at Arxiv.

  


### `GET /get_data`
Fetch aggregated data with flexible grouping.

**Required Parameters:**
- `model` (string): Target database model (e.g. `"hourly_download_data"`)
- `group_by` (string): Primary grouping column (must exist in model)

**Optional Parameters:**
- `second_group_by` (string): Secondary grouping column
- `time_group` (string): Time aggregation (`"year"`, `"month"`, or `"day"`)

  

**Returns:**

  

200 OK: A JSON array of objects, using lists in its keys if neccessary. If it does use a list, the same indexes in each list correspond to one data point. For example, http://localhost:8080/api/get_data?model=hourly&group_by=category&second_group_by=country will fetch results similar to

  

```javascript

[

{

"category":  "astro-ph",

"country": [

"Albania",

"Algeria",

"Argentina",...

],

"data": [

"1",

"5",

"14",...

]

}...

]

```

Where data is always the primary counts aggregated by given parameters. Other keys should match other parameters specified.


### `GET /get_global_sum`

Get total sums aggregated by time period.

**Required Parameters:**

-   `model`  (string): Target database model (e.g. `"hourly_download_data"`)
    
-   `time_group`  (string): Aggregation period (`"year"`,  `"month"`,  `"day"`, or  `"hour"`)
  
  ### `GET /get_todays_downloads`

Get today's downloads by hour (timezone-aware).

**Optional Parameter:**

-   `timezone`  (string): Timezone for hour alignment (default:  `"UTC"`)
    

**Currently Supported Timezones:**

-   Americas:  `America/New_York`,  `America/Chicago`,  `America/Denver`,  `America/Los_Angeles`
    
-   Europe:  `Europe/London`,  `Europe/Berlin`
    
-   Asia/Pacific:  `Asia/Tokyo`,  `Asia/Shanghai`,  `Asia/Kolkata`,  `Australia/Sydney`



**Overall Returns:**
- 400 Bad Request: If required parameters are missing or invalid.
- 500 Internal Server Error: For any server-side errors.

## Testing

- TBD