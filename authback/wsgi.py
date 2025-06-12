"""
WSGI config for authback project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Apply the Jet patch before Django starts
try:
    from jet_patch import patch_jet
    patch_jet()
    print("Django Jet patch applied successfully")
except Exception as e:
    print(f"Failed to apply Django Jet patch: {e}")

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'authback.settings')

application = get_wsgi_application()
