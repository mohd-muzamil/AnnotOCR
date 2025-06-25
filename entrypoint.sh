#!/bin/bash
# Ensure necessary directories exist before starting the application
mkdir -p /app/db
mkdir -p /app/static/images
mkdir -p /app/static/data

# Note: Permission setting commands are omitted to avoid 'Operation not permitted' errors in Docker environment
# Directories are created with default permissions

# Start Gunicorn without specifying user due to user 1017 not existing
exec gunicorn --bind 0.0.0.0:5000 "wsgi:app"
