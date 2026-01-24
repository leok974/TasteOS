import pytest
from app.parsing.token_encoder import (
    encode_recipe_token,
    decode_recipe_token,
    TokenError,
    TokenVersionError,
    TokenTooLargeError,
    TokenCorruptedError,
    MAX_TOKEN_LENGTH,
    MAX_DECOMPRESSED_SIZE
)

def test_token_roundtrip_with_checksum():
    """Test encoding and decoding preserves data with checksum validation."""
    data = {
        "recipe": {
            "title": "Test Recipe",
            "ingredients": [{"name": "flour", "qty": 2, "unit": "cups"}],
            "steps": [{"step_index": 0, "title": "Mix", "bullets": ["Stir"]}]
        }
    }
    
    token = encode_recipe_token(data)
    
    # Verify token format: tasteos-v1:{64-char-hex}:{base64}
    assert token.startswith("tasteos-v1:")
    parts = token[len("tasteos-v1:"):].split(":", 1)
    assert len(parts) == 2
    checksum, b64_data = parts
    assert len(checksum) == 64
    assert all(c in '0123456789abcdef' for c in checksum)
    
    # Decode and verify
    decoded = decode_recipe_token(token)
    assert decoded == data

def test_token_checksum_tampering_detected():
    """Test that modifying token data invalidates checksum."""
    data = {"recipe": {"title": "Original"}}
    token = encode_recipe_token(data)
    
    # Tamper with checksum (change last char)
    parts = token.split(":")
    tampered_checksum = parts[1][:-1] + ('0' if parts[1][-1] != '0' else '1')
    tampered_token = f"{parts[0]}:{tampered_checksum}:{parts[2]}"
    
    with pytest.raises(TokenCorruptedError, match="checksum mismatch"):
        decode_recipe_token(tampered_token)

def test_token_size_limit_exceeded():
    """Test that oversized recipes are rejected."""
    # Create recipe data larger than MAX_DECOMPRESSED_SIZE
    huge_data = {
        "recipe": {
            "title": "x" * (MAX_DECOMPRESSED_SIZE + 1000),
            "ingredients": []
        }
    }
    
    with pytest.raises(TokenTooLargeError, match="Recipe data too large"):
        encode_recipe_token(huge_data)

def test_token_invalid_prefix():
    """Test that tokens without proper prefix are rejected."""
    with pytest.raises(TokenCorruptedError, match="prefix"):
        decode_recipe_token("invalid:checksum:data")

def test_token_malformed_structure():
    """Test that tokens without checksum separator are rejected."""
    with pytest.raises(TokenCorruptedError, match="missing checksum or data"):
        decode_recipe_token("tasteos-v1:onlyonepart")

def test_token_invalid_checksum_format():
    """Test that non-hex checksums are rejected."""
    with pytest.raises(TokenCorruptedError, match="checksum"):
        decode_recipe_token("tasteos-v1:ZZZZ_not_hex_ZZZZ:somedata")

def test_token_corrupted_base64():
    """Test that invalid base64 is handled gracefully."""
    valid_checksum = "a" * 64
    invalid_b64 = "!!!invalid!!!"
    token = f"tasteos-v1:{valid_checksum}:{invalid_b64}"
    
    with pytest.raises(TokenCorruptedError):
        decode_recipe_token(token)

def test_token_size_check_before_processing():
    """Test that oversized tokens are rejected before any processing."""
    # Create a token that's too long
    long_token = "tasteos-v1:" + "a" * (MAX_TOKEN_LENGTH + 1000)
    
    with pytest.raises(TokenTooLargeError, match="too large"):
        decode_recipe_token(long_token)

def test_backwards_compatibility_old_tokens_fail():
    """Test that old format tokens (without checksum) are properly rejected."""
    import base64
    import gzip
    import json
    
    # Create old-format token (no checksum)
    data = {"recipe": {"title": "Old Format"}}
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
    compressed = gzip.compress(json_bytes)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    old_token = f"tasteos-v1:{b64}"
    
    # Should fail with "missing checksum or data" since there's no second colon
    with pytest.raises(TokenCorruptedError, match="missing checksum or data"):
        decode_recipe_token(old_token)
