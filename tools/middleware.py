from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import re

class CacheControlMiddleware(MiddlewareMixin):
    """
    Middleware to add Cache-Control headers to responses
    """
    
    # Django 5.2+ requires this attribute to be defined
    async_mode = False
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        
        # Compile regex patterns for static and media URLs
        self.static_url_pattern = re.compile(f'^{settings.STATIC_URL}')
        self.media_url_pattern = re.compile(f'^{settings.MEDIA_URL}')
        
        # File extension patterns
        self.image_extensions = re.compile(r'\.(jpg|jpeg|png|gif|webp|svg|avif)$', re.IGNORECASE)
        self.css_js_extensions = re.compile(r'\.(css|js)$', re.IGNORECASE)
        self.font_extensions = re.compile(r'\.(woff|woff2|ttf|eot|otf)$', re.IGNORECASE)
        
    def process_response(self, request, response):
        path = request.path_info.lstrip('/')
        
        # Skip if Cache-Control is already set
        if 'Cache-Control' in response:
            return response
        
        # Static files
        if self.static_url_pattern.match(path):
            if self.css_js_extensions.search(path):
                # CSS and JS files - 1 week
                response['Cache-Control'] = 'public, max-age=604800, stale-while-revalidate=86400'
            elif self.font_extensions.search(path):
                # Fonts - 1 month
                response['Cache-Control'] = 'public, max-age=2592000, stale-while-revalidate=86400'
            else:
                # Other static files - 1 day
                response['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'
            
            # Add ETag support
            if 'ETag' not in response:
                response['ETag'] = f'W/"{hash(response.content)}"'
        
        # Media files
        elif self.media_url_pattern.match(path):
            if self.image_extensions.search(path):
                # Images - 1 week
                response['Cache-Control'] = 'public, max-age=604800, stale-while-revalidate=86400'
            else:
                # Other media - 1 day
                response['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'
            
            # Add ETag support
            if 'ETag' not in response:
                response['ETag'] = f'W/"{hash(response.content)}"'
        
        return response 