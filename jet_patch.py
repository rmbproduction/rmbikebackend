"""
This patch fixes the import issue in Django Jet for Django 5.2 compatibility.
"""

import os
import sys
from pathlib import Path
import importlib.util

def patch_jet():
    """
    Patch the Django Jet module to use gettext_lazy instead of ugettext_lazy
    """
    try:
        # Try to find the jet module path
        jet_spec = importlib.util.find_spec('jet')
        if not jet_spec:
            print("Django Jet module not found")
            return False
        
        jet_path = Path(jet_spec.origin).parent
        models_path = jet_path / 'models.py'
        
        if not models_path.exists():
            print(f"Jet models file not found at {models_path}")
            return False
        
        # Read the content of models.py
        with open(models_path, 'r') as f:
            content = f.read()
        
        # Check if the file already uses gettext_lazy
        if 'from django.utils.translation import gettext_lazy as _' in content:
            print("Jet models file already patched")
            return True
        
        # Replace ugettext_lazy with gettext_lazy
        content = content.replace(
            'from django.utils.translation import ugettext_lazy as _',
            'from django.utils.translation import gettext_lazy as _'
        )
        
        # Write the updated content back
        with open(models_path, 'w') as f:
            f.write(content)
        
        print("Successfully patched Django Jet models.py")
        return True
    
    except Exception as e:
        print(f"Error patching Django Jet: {e}")
        return False

if __name__ == "__main__":
    patch_jet() 