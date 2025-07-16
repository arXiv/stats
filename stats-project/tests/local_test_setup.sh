#!/bin/bash
# Use this script to automate the setup of your local testing environment.
# This script assumes you have Docker and Docker Compose installed.

# Stop script on errors
set -e

echo "Starting MySQL and PostgreSQL containers..."

# Start MySQL and PostgreSQL containers using Docker
docker-compose -f docker-compose.yaml up -d

# Wait for databases to be ready
echo "Giving Database containers 10 seconds to start..."
sleep 10  # Adjust if needed

# start injecting the test data
echo "Injecting test data into MySQL and PostgreSQL..."
python inject_data.py

echo "Setup complete!"
