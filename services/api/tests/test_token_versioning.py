import pytest
from app.parsing.token_encoder import (
    encode_recipe_token,
    decode_recipe_token,
    TokenError,
    TokenVersionError,
    TokenTooLargeError,
    TokenCorruptedError,
)

def test_checksum_over_compressed_bytes():
    """Verify checksum is computed over compressed bytes, not JSON."""
    data = {"recipe": {"title": "Test"}}
    
    # Encode token
    token = encode_recipe_token(data)
    
    # Token should decode successfully
    decoded = decode_recipe_token(token)
    assert decoded == data
    
    # Modify the base64 data (after checksum) should fail validation
    parts = token.split(":")
    tampered_data = parts[2][:-1] + ('A' if parts[2][-1] != 'A' else 'B')
    tampered_token = f"{parts[0]}:{parts[1]}:{tampered_data}"
    
    with pytest.raises(TokenCorruptedError, match="checksum mismatch"):
        decode_recipe_token(tampered_token)

def test_unknown_version_rejected():
    """Reject tokens with unsupported versions."""
    # Create a fake v2 token
    fake_v2_token = "tasteos-v2:abc123..."
    
    with pytest.raises(TokenVersionError, match="Unsupported token version: 'v2'"):
        decode_recipe_token(fake_v2_token)

def test_missing_prefix_error():
    """Token without tasteos- prefix should give helpful error."""
    invalid_token = "random-data:abc:def"
    
    with pytest.raises(TokenCorruptedError, match="missing 'tasteos-' prefix"):
        decode_recipe_token(invalid_token)

def test_token_too_large_helpful_error():
    """Oversized token should give specific error."""
    huge_token = "tasteos-v1:" + "a" * (101 * 1024)
    
    with pytest.raises(TokenTooLargeError, match="Token too large"):
        decode_recipe_token(huge_token)


def test_truncated_token_error():
    """Truncated token should give helpful error."""
    # Token with only checksum, no data
    truncated = "tasteos-v1:abc123"
    
    with pytest.raises(TokenCorruptedError, match="truncated or corrupted"):
        decode_recipe_token(truncated)

def test_forward_compatibility_structure():
    """Ensure v1 decoder is isolated for future v2."""
    data = {"recipe": {"title": "Test"}}
    token = encode_recipe_token(data)
    
    # Should use v1 decoder
    decoded = decode_recipe_token(token)
    assert decoded == data
    
    # Version is extracted correctly
    assert "tasteos-v1:" in token
