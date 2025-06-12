#!/bin/bash

# Deployment script for Railway

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Apply the Django Jet patch
echo "Applying Django Jet patch..."
python -c "from jet_patch import patch_jet; patch_jet()"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply migrations
echo "Applying migrations..."
python manage.py migrate

echo "Deployment complete!" 