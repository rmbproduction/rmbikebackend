from django.core.cache import cache
from django.conf import settings
from functools import wraps
from django.http import HttpResponse
import hashlib
import logging
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)

def get_cache_key(request, key_prefix="view"):
    """
    Generate a cache key based on request path and query params
    """
    query_params = request.GET.copy()
    # Remove non-deterministic params like timestamps
    if 'timestamp' in query_params:
        del query_params['timestamp']
    if 't' in query_params:
        del query_params['t']
    
    # Generate a key based on the path and sorted query params
    key_parts = [key_prefix, request.path]
    for key in sorted(query_params.keys()):
        key_parts.append(f"{key}:{query_params[key]}")
    
    # Generate a hash of the key parts
    key_string = "_".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def ensure_renderer(response):
    """
    Ensure the response has a renderer set
    """
    if isinstance(response, Response) and not hasattr(response, 'accepted_renderer'):
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
    return response

def cache_api_response(timeout=None, key_prefix="api"):
    """
    Cache API responses for a specified time
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            try:
                # Determine if this is a ViewSet method or a regular view
                request = None
                
                # Case 1: ViewSet method (self is first arg, request is self.request)
                if len(args) > 0 and hasattr(args[0], 'request'):
                    self = args[0]
                    request = self.request
                    
                # Case 2: Regular view (request is first arg)
                elif len(args) > 0 and hasattr(args[0], 'method'):
                    request = args[0]
                    
                # If we can't identify the request, just pass through to the original function
                if request is None:
                    logger.warning(f"Could not identify request in cache wrapper for {view_func.__name__}")
                    return ensure_renderer(view_func(*args, **kwargs))
                
                # Skip caching for non-GET requests
                if request.method != 'GET':
                    return ensure_renderer(view_func(*args, **kwargs))
                
                # Skip caching if user is authenticated and cache_auth=False
                if request.user.is_authenticated and not getattr(settings, 'CACHE_AUTHENTICATED_REQUESTS', True):
                    return ensure_renderer(view_func(*args, **kwargs))
                
                # Use provided timeout or default
                cache_timeout = timeout or getattr(settings, 'CACHE_TTL', 60 * 5)
                
                # Generate cache key
                cache_key = get_cache_key(request, key_prefix)
                
                # Try to get from cache
                response = cache.get(cache_key)
                if response:
                    logger.debug(f"Cache hit: {cache_key}")
                    # Ensure cached response has renderer
                    return ensure_renderer(response)
                
                # Generate response
                response = view_func(*args, **kwargs)
                
                # Cache the response if it's successful
                if response.status_code == 200:
                    # Ensure response has renderer before caching
                    response = ensure_renderer(response)
                    
                    # If it's a DRF response, render it first before caching
                    if isinstance(response, Response) and not getattr(response, '_is_rendered', False):
                        response.render()
                    
                    cache.set(cache_key, response, cache_timeout)
                    logger.debug(f"Cached: {cache_key} for {cache_timeout} seconds")
                
                return response
            except Exception as e:
                # If any error occurs in the caching logic, log it and pass through to the original function
                logger.exception(f"Error in cache wrapper for {view_func.__name__}: {str(e)}")
                return ensure_renderer(view_func(*args, **kwargs))
        return wrapper
    return decorator

def cache_page_by_user(timeout=None, key_prefix="page"):
    """
    Cache pages by URL and user ID
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            try:
                # Determine if this is a ViewSet method or a regular view
                request = None
                
                # Case 1: ViewSet method (self is first arg, request is self.request)
                if len(args) > 0 and hasattr(args[0], 'request'):
                    self = args[0]
                    request = self.request
                    
                # Case 2: Regular view (request is first arg)
                elif len(args) > 0 and hasattr(args[0], 'method'):
                    request = args[0]
                    
                # If we can't identify the request, just pass through to the original function
                if request is None:
                    logger.warning(f"Could not identify request in cache wrapper for {view_func.__name__}")
                    return ensure_renderer(view_func(*args, **kwargs))
                
                # Skip caching for non-GET requests
                if request.method != 'GET':
                    return ensure_renderer(view_func(*args, **kwargs))
                
                # Use provided timeout or default
                cache_timeout = timeout or getattr(settings, 'CACHE_TTL', 60 * 5)
                
                # Generate cache key with user ID
                user_id = request.user.id if request.user.is_authenticated else 'anonymous'
                key_parts = [key_prefix, request.path, str(user_id)]
                cache_key = hashlib.md5("_".join(key_parts).encode()).hexdigest()
                
                # Try to get from cache
                response = cache.get(cache_key)
                if response:
                    logger.debug(f"Cache hit: {cache_key}")
                    # Ensure cached response has renderer
                    return ensure_renderer(response)
                
                # Generate response
                response = view_func(*args, **kwargs)
                
                # Cache the response if it's successful
                if response.status_code == 200:
                    # Ensure response has renderer before caching
                    response = ensure_renderer(response)
                    
                    # If it's a DRF response, render it first before caching
                    if isinstance(response, Response) and not getattr(response, '_is_rendered', False):
                        response.render()
                    
                    cache.set(cache_key, response, cache_timeout)
                    logger.debug(f"Cached: {cache_key} for {cache_timeout} seconds")
                
                return response
            except Exception as e:
                # If any error occurs in the caching logic, log it and pass through to the original function
                logger.exception(f"Error in cache wrapper for {view_func.__name__}: {str(e)}")
                return ensure_renderer(view_func(*args, **kwargs))
        return wrapper
    return decorator

# Custom cache time constants for different data types
CACHE_TIMES = {
    'STATIC': 60 * 60 * 24,  # 24 hours for static data
    'LOOKUP': 60 * 60,       # 1 hour for lookup data
    'DYNAMIC': 60 * 5,       # 5 minutes for dynamic data
    'USER': 60 * 1           # 1 minute for user-specific data
} 