import json
import gzip
import base64
from typing import Dict, Any

PREFIX = "tasteos-v1:"

def encode_recipe_token(data: Dict[str, Any]) -> str:
    """Compress and encode recipe data into a share token."""
    # 1. Compact JSON
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    # 2. Gzip
    compressed = gzip.compress(json_bytes)
    # 3. Base64 (URL safe)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    # 4. Prefix
    return f"{PREFIX}{b64}"

def decode_recipe_token(token: str) -> Dict[str, Any]:
    """Decode a share token back into recipe data."""
    if not token.startswith(PREFIX):
        raise ValueError("Invalid token format")
    
    b64 = token[len(PREFIX):]
    try:
        compressed = base64.urlsafe_b64decode(b64)
        json_bytes = gzip.decompress(compressed)
        return json.loads(json_bytes.decode('utf-8'))
    except Exception as e:
        raise ValueError(f"Failed to decode token: {str(e)}")
