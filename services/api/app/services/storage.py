import os
import logging
from pathlib import Path
from ..settings import settings

logger = logging.getLogger("tasteos.storage")

# Use settings or default
MEDIA_ROOT = Path(settings.media_root) if hasattr(settings, "media_root") and settings.media_root else (Path(os.getcwd()) / "media")

class LocalStorage:
    def __init__(self):
        if not MEDIA_ROOT.exists():
            MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    
    def put_bytes(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """
        Save bytes to local disk.
        key: recipes/{recipe_id}/images/{image_id}.jpg
        Returns: Public relative URL
        """
        # Ensure strict path safety (simple check)
        if ".." in key:
            raise ValueError("Invalid storage key")

        file_path = MEDIA_ROOT / key
        
        # Ensure parent dir exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(data)
            
        logger.info(f"Saved {len(data)} bytes to {file_path}")
        
        # Return URL path
        return f"/media/{key}"

    def exists(self, key: str) -> bool:
        return (MEDIA_ROOT / key).exists()

# Singleton
storage = LocalStorage()
