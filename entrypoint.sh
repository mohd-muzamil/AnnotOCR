#!/bin/bash
# Ensure necessary directories exist before starting the application
mkdir -p /app/db
mkdir -p /app/static/images
mkdir -p /app/static/data

# Note: Permission setting commands are omitted to avoid 'Operation not permitted' errors in Docker environment
# Directories are created with default permissions

# Start Gunicorn without specifying user due to user 1017 not existing
# Set timeout to 120 seconds to allow more time for OCR processing
exec gunicorn --bind 0.0.0.0:5000 --timeout 120 "wsgi:app"
