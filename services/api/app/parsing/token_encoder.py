import json
import gzip
import base64
import hashlib
from typing import Dict, Any

PREFIX = "tasteos-v1:"

# Security limits
MAX_TOKEN_LENGTH = 100 * 1024  # 100KB base64
MAX_DECOMPRESSED_SIZE = 1 * 1024 * 1024  # 1MB JSON

def encode_recipe_token(data: Dict[str, Any]) -> str:
    """Compress and encode recipe data into a secure share token.
    
    Format: tasteos-v1:{sha256_hex}:{base64_gzipped_json}
    """
    # 1. Compact JSON
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    
    # Check size before compression
    if len(json_bytes) > MAX_DECOMPRESSED_SIZE:
        raise ValueError(f"Recipe data too large: {len(json_bytes)} bytes (max {MAX_DECOMPRESSED_SIZE})")
    
    # 2. Gzip
    compressed = gzip.compress(json_bytes, compresslevel=9)
    
    # 3. Base64 (URL safe)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    
    # 4. Checksum (SHA256 of compressed data)
    checksum = hashlib.sha256(compressed).hexdigest()
    
    # 5. Assemble token
    token = f"{PREFIX}{checksum}:{b64}"
    
    # Final size check
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError(f"Token too large: {len(token)} chars (max {MAX_TOKEN_LENGTH})")
    
    return token

def decode_recipe_token(token: str) -> Dict[str, Any]:
    """Decode a share token back into recipe data with security checks.
    
    Raises:
        ValueError: If token is invalid, corrupted, or exceeds size limits
    """
    # 1. Strict prefix check
    if not token.startswith(PREFIX):
        raise ValueError("Invalid token format: missing prefix")
    
    # 2. Size check (before processing)
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError(f"Token too large: {len(token)} chars (max {MAX_TOKEN_LENGTH})")
    
    # 3. Parse token structure
    token_body = token[len(PREFIX):]
    parts = token_body.split(':', 1)
    
    if len(parts) != 2:
        raise ValueError("Invalid token format: missing checksum or data")
    
    expected_checksum, b64 = parts
    
    # Validate checksum format (64 hex chars for SHA256)
    if len(expected_checksum) != 64 or not all(c in '0123456789abcdef' for c in expected_checksum):
        raise ValueError("Invalid token format: malformed checksum")
    
    try:
        # 4. Decode base64
        compressed = base64.urlsafe_b64decode(b64)
        
        # 5. Verify checksum BEFORE decompression (zip-bomb protection)
        actual_checksum = hashlib.sha256(compressed).hexdigest()
        if actual_checksum != expected_checksum:
            raise ValueError("Token corrupted: checksum mismatch")
        
        # 6. Safe decompression with size limit
        json_bytes = _safe_decompress(compressed, MAX_DECOMPRESSED_SIZE)
        
        # 7. Parse JSON
        return json.loads(json_bytes.decode('utf-8'))
        
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to decode token: invalid encoding - {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode token: invalid JSON - {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to decode token: {str(e)}")

def _safe_decompress(compressed: bytes, max_size: int) -> bytes:
    """Safely decompress gzip data with size limit to prevent zip-bombs.
    
    Args:
        compressed: Gzipped bytes
        max_size: Maximum allowed decompressed size
        
    Returns:
        Decompressed bytes
        
    Raises:
        ValueError: If decompressed size exceeds max_size
    """
    try:
        # Decompress and check size
        decompressed = gzip.decompress(compressed)
        
        if len(decompressed) > max_size:
            raise ValueError(f"Decompressed data too large: {len(decompressed)} bytes (max {max_size})")
        
        return decompressed
    except gzip.BadGzipFile:
        raise ValueError("Invalid gzip data")

