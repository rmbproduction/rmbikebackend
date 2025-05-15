from django.core.cache import cache
from django.conf import settings
from functools import wraps
from django.http import HttpResponse
import hashlib
import logging

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

def cache_api_response(timeout=None, key_prefix="api"):
    """
    Cache API responses for a specified time
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            try:
                # Determine if this is a ViewSet method or a regular view
                if len(args) > 0 and hasattr(args[0], 'request'):
                    # This is a ViewSet method call where self is the first argument
                    self = args[0]
                    request = self.request
                elif len(args) > 0 and hasattr(args[0], 'method'):
                    # This is a regular view where request is the first argument
                    request = args[0]
                else:
                    # If we can't identify the request, just pass through to the original function
                    logger.warning(f"Could not identify request in cache wrapper for {view_func.__name__}")
                    return view_func(*args, **kwargs)
                
                # Skip caching for non-GET requests
                if request.method != 'GET':
                    return view_func(*args, **kwargs)
                
                # Skip caching if user is authenticated and cache_auth=False
                if request.user.is_authenticated and not getattr(settings, 'CACHE_AUTHENTICATED_REQUESTS', True):
                    return view_func(*args, **kwargs)
                
                # Use provided timeout or default
                cache_timeout = timeout or getattr(settings, 'CACHE_TTL', 60 * 5)
                
                # Generate cache key
                cache_key = get_cache_key(request, key_prefix)
                
                # Try to get from cache
                response = cache.get(cache_key)
                if response:
                    logger.debug(f"Cache hit: {cache_key}")
                    return HttpResponse(content=response.content,
                                    status=response.status_code,
                                    content_type=response.content_type)
                
                # Generate response
                response = view_func(*args, **kwargs)
                
                # Cache the response if it's successful
                if response.status_code == 200:
                    cache.set(cache_key, response, cache_timeout)
                    logger.debug(f"Cached: {cache_key} for {cache_timeout} seconds")
                
                return response
            except Exception as e:
                # If any error occurs in the caching logic, log it and pass through to the original function
                logger.exception(f"Error in cache wrapper for {view_func.__name__}: {str(e)}")
                return view_func(*args, **kwargs)
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
                if len(args) > 0 and hasattr(args[0], 'request'):
                    # This is a ViewSet method call where self is the first argument
                    self = args[0]
                    request = self.request
                elif len(args) > 0 and hasattr(args[0], 'method'):
                    # This is a regular view where request is the first argument
                    request = args[0]
                else:
                    # If we can't identify the request, just pass through to the original function
                    logger.warning(f"Could not identify request in cache wrapper for {view_func.__name__}")
                    return view_func(*args, **kwargs)
                
                # Skip caching for non-GET requests
                if request.method != 'GET':
                    return view_func(*args, **kwargs)
                
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
                    return HttpResponse(content=response.content,
                                    status=response.status_code,
                                    content_type=response.content_type)
                
                # Generate response
                response = view_func(*args, **kwargs)
                
                # Cache the response if it's successful
                if response.status_code == 200:
                    cache.set(cache_key, response, cache_timeout)
                    logger.debug(f"Cached: {cache_key} for {cache_timeout} seconds")
                
                return response
            except Exception as e:
                # If any error occurs in the caching logic, log it and pass through to the original function
                logger.exception(f"Error in cache wrapper for {view_func.__name__}: {str(e)}")
                return view_func(*args, **kwargs)
        return wrapper
    return decorator

# Custom cache time constants for different data types
CACHE_TIMES = {
    'STATIC': 60 * 60 * 24,  # 24 hours for static data
    'LOOKUP': 60 * 60,       # 1 hour for lookup data
    'DYNAMIC': 60 * 5,       # 5 minutes for dynamic data
    'USER': 60 * 1           # 1 minute for user-specific data
} 