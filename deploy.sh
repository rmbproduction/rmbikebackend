#!/bin/bash

# Deployment script for Railway

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Apply the Django Jet patch
echo "Applying Django Jet patch..."
python -c "from jet_patch import patch_jet; patch_jet()"

# Create static directories if they don't exist
echo "Creating static directories..."
mkdir -p static/css static/js static/img

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply migrations
echo "Applying migrations..."
python manage.py migrate

echo "Deployment complete!" 