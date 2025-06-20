#!/bin/bash

# No database readiness check needed for SQLite3

# Apply database migrations
flask db upgrade

# Load initial data
flask shell <<EOF
from services.data_loader import load_images_from_static
load_images_from_static()
exit()
EOF

# Run OCR image extraction on initial build
flask shell <<EOF
from services.ocr_image_extractor import generate_ocr_for_all_images
generate_ocr_for_all_images()
exit()
EOF

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:5000 "wsgi:app"
