#!/bin/bash

# use this script to automate running the test scripts for the  backend API.
# This script assumes you have run the local_test_setup.sh script to set up the database containers.

# Stop script on errors
set -e

echo "Running the backend..."
python ../stats_api/factory.py

echo "Running test 01..."
python -m unittest tests/test_api.py