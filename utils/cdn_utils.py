from django.conf import settings
from django.core.cache import cache
from typing import Dict, List, Optional
from functools import lru_cache
import cloudinary
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

class CDNManager:
    """Centralized CDN URL management for the entire application"""
    
    def __init__(self):
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
        self.api_key = settings.CLOUDINARY_API_KEY
        self.api_secret = settings.CLOUDINARY_API_SECRET
        
        # Default transformations for different use cases
        self.transformations = {
            'vehicle': {
                'thumbnail': 'c_thumb,w_300,h_200,q_auto',
                'preview': 'c_fill,w_800,h_600,q_auto',
                'full': 'c_fill,w_1920,h_1080,q_auto',
                'compressed': 'c_fill,w_600,h_400,q_60'
            },
            'profile': {
                'small': 'c_thumb,w_100,h_100,q_auto',
                'medium': 'c_fill,w_400,h_400,q_auto'
            },
            'document': {
                'preview': 'c_fill,w_800,h_600,q_auto'
            }
        }

        # Cache settings
        self.cache_timeout = 86400  # 24 hours

    def _get_cache_key(self, resource_type: str, resource_id: str, view: str, size: str) -> str:
        """Generate cache key for CDN URLs"""
        return f"cdn:{resource_type}:{resource_id}:{view}:{size}"

    def _build_url(self, path: str, transformation: str) -> str:
        """Build CDN URL with transformation"""
        return f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{transformation}/{path}"

    @lru_cache(maxsize=100)
    def get_vehicle_image_url(
        self, 
        vehicle_id: int, 
        view: str = 'front', 
        size: str = 'preview',
        use_cache: bool = True
    ) -> str:
        """Get vehicle image URL with optional caching"""
        if use_cache:
            cache_key = self._get_cache_key('vehicle', str(vehicle_id), view, size)
            cached_url = cache.get(cache_key)
            if cached_url:
                return cached_url

        transformation = self.transformations['vehicle'].get(size, self.transformations['vehicle']['preview'])
        url = self._build_url(f"vehicles/{vehicle_id}/{view}", transformation)

        if use_cache:
            cache.set(cache_key, url, timeout=self.cache_timeout)
        
        return url

    def get_vehicle_all_views(
        self, 
        vehicle_id: int,
        views: List[str] = ['front', 'back', 'left', 'right']
    ) -> Dict[str, Dict[str, str]]:
        """Get all image URLs for a vehicle"""
        return {
            view: {
                size: self.get_vehicle_image_url(vehicle_id, view, size)
                for size in self.transformations['vehicle'].keys()
            }
            for view in views
        }

    def get_document_url(
        self, 
        doc_type: str,
        doc_id: str,
        size: str = 'preview'
    ) -> str:
        """Get document image URL"""
        transformation = self.transformations['document'][size]
        return self._build_url(f"documents/{doc_type}/{doc_id}", transformation)

    def get_profile_image_url(
        self,
        user_id: int,
        size: str = 'medium'
    ) -> str:
        """Get profile image URL"""
        transformation = self.transformations['profile'][size]
        return self._build_url(f"profiles/{user_id}", transformation)

    def get_upload_params(
        self,
        resource_type: str,
        resource_id: str,
        extra_options: Dict = None
    ) -> Dict:
        """Get upload parameters for frontend"""
        base_options = {
            'cloud_name': self.cloud_name,
            'folder': f"{resource_type}s/{resource_id}",
            'resource_type': 'auto',
            'quality': 'auto:good'
        }
        
        if extra_options:
            base_options.update(extra_options)
            
        return base_options

    def clear_cache(self, resource_type: str, resource_id: str) -> None:
        """Clear all cached URLs for a resource"""
        pattern = f"cdn:{resource_type}:{resource_id}:*"
        keys = cache.keys(pattern)
        if keys:
            cache.delete_many(keys)

# Create singleton instance
cdn_manager = CDNManager() 