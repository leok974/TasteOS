import json
import gzip
import base64
import hashlib
from typing import Dict, Any
from enum import Enum

# Supported token versions
SUPPORTED_VERSIONS = {"v1"}
CURRENT_VERSION = "v1"
PREFIX = f"tasteos-{CURRENT_VERSION}:"

# Security limits
MAX_TOKEN_LENGTH = 100 * 1024  # 100KB base64
MAX_DECOMPRESSED_SIZE = 1 * 1024 * 1024  # 1MB JSON

class TokenError(Exception):
    """Base exception for token-related errors."""
    pass

class TokenVersionError(TokenError):
    """Token version not supported."""
    pass

class TokenTooLargeError(TokenError):
    """Token exceeds size limits."""
    pass

class TokenCorruptedError(TokenError):
    """Token checksum mismatch or invalid format."""
    pass

def encode_recipe_token(data: Dict[str, Any]) -> str:
    """Compress and encode recipe data into a secure share token.
    
    Format: tasteos-v1:{sha256_hex}:{base64_gzipped_json}
    
    The checksum is computed over the compressed (gzipped) bytes,
    ensuring copy/paste differences don't create false negatives.
    """
    # 1. Compact JSON
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    
    # Check size before compression
    if len(json_bytes) > MAX_DECOMPRESSED_SIZE:
        raise TokenTooLargeError(f"Recipe data too large: {len(json_bytes)} bytes (max {MAX_DECOMPRESSED_SIZE})")
    
    # 2. Gzip compress
    compressed = gzip.compress(json_bytes, compresslevel=9)
    
    # 3. Checksum OVER COMPRESSED BYTES (not JSON)
    # This ensures copy/paste doesn't affect validation
    checksum = hashlib.sha256(compressed).hexdigest()
    
    # 4. Base64 encode (URL safe)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    
    # 5. Assemble token
    token = f"{PREFIX}{checksum}:{b64}"
    
    # Final size check
    if len(token) > MAX_TOKEN_LENGTH:
        raise TokenTooLargeError(f"Token too large: {len(token)} chars (max {MAX_TOKEN_LENGTH})")
    
    return token

def decode_recipe_token(token: str) -> Dict[str, Any]:
    """Decode a share token back into recipe data with comprehensive validation.
    
    Raises:
        TokenVersionError: If token version is unsupported
        TokenTooLargeError: If token exceeds size limits
        TokenCorruptedError: If checksum fails or data is invalid
        TokenError: For other token-related errors
    """
    # 1. Size check (before any processing)
    if len(token) > MAX_TOKEN_LENGTH:
        raise TokenTooLargeError(
            f"Token too large: {len(token)} chars (max {MAX_TOKEN_LENGTH}). "
            f"Token may be corrupted or from a future version."
        )
    
    # 2. Version check with helpful error
    if not token.startswith("tasteos-"):
        raise TokenCorruptedError(
            "Invalid token format: missing 'tasteos-' prefix. "
            "This doesn't appear to be a valid TasteOS share token."
        )
    
    # Extract version
    try:
        version_end = token.index(":", 8)  # After "tasteos-"
        version = token[8:version_end]  # Extract version (e.g., "v1")
    except ValueError:
        raise TokenCorruptedError("Invalid token format: missing version separator")
    
    # Validate version
    if version not in SUPPORTED_VERSIONS:
        raise TokenVersionError(
            f"Unsupported token version: '{version}'. "
            f"This token may be from a newer version of TasteOS. "
            f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
        )
    
    # 3. Route to version-specific decoder
    if version == "v1":
        return _decode_v1_token(token)
    
    # Fallback (should never reach due to version check above)
    raise TokenVersionError(f"No decoder available for version: {version}")

def _decode_v1_token(token: str) -> Dict[str, Any]:
    """Decode a v1 format token.
    
    Format: tasteos-v1:{checksum}:{base64_data}
    """
    # Parse token structure
    token_body = token[len(PREFIX):]
    parts = token_body.split(':', 1)
    
    if len(parts) != 2:
        raise TokenCorruptedError(
            "Invalid v1 token format: missing checksum or data section. "
            "Token may be truncated or corrupted."
        )
    
    expected_checksum, b64 = parts
    
    # Validate checksum format (64 hex chars for SHA256)
    if len(expected_checksum) != 64 or not all(c in '0123456789abcdef' for c in expected_checksum):
        raise TokenCorruptedError(
            "Invalid checksum format. Token may be corrupted or modified."
        )
    
    try:
        # Decode base64
        compressed = base64.urlsafe_b64decode(b64)
    except Exception as e:
        raise TokenCorruptedError(
            f"Failed to decode token data: {str(e)}. "
            f"Token may be corrupted or incomplete."
        )
    
    # Verify checksum BEFORE decompression (zip-bomb protection)
    # Checksum is computed over compressed bytes
    actual_checksum = hashlib.sha256(compressed).hexdigest()
    if actual_checksum != expected_checksum:
        raise TokenCorruptedError(
            "Token integrity check failed: checksum mismatch. "
            "Token has been modified or corrupted in transit."
        )
    
    # Safe decompression with size limit
    try:
        json_bytes = _safe_decompress(compressed, MAX_DECOMPRESSED_SIZE)
    except TokenTooLargeError:
        raise  # Re-raise with original message
    except Exception as e:
        raise TokenCorruptedError(
            f"Failed to decompress token data: {str(e)}. "
            f"Token may be corrupted."
        )
    
    # Parse JSON
    try:
        return json.loads(json_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise TokenCorruptedError(
            f"Invalid recipe data in token: {str(e)}. "
            f"Token contents are corrupted."
        )
    except UnicodeDecodeError as e:
        raise TokenCorruptedError(f"Invalid text encoding in token: {str(e)}")

def _safe_decompress(compressed: bytes, max_size: int) -> bytes:
    """Safely decompress gzip data with size limit to prevent zip-bombs."""
    try:
        # Decompress and check size
        decompressed = gzip.decompress(compressed)
        
        if len(decompressed) > max_size:
            raise TokenTooLargeError(
                f"Decompressed data too large: {len(decompressed)} bytes (max {max_size}). "
                f"This may indicate a corrupted or malicious token."
            )
        
        return decompressed
    except gzip.BadGzipFile:
        raise TokenCorruptedError("Invalid compressed data in token")

