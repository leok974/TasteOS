"""
Test login endpoint and capture detailed errors.
"""
import requests
import json

url = "http://localhost:8000/api/v1/auth/login"
payload = {
    "email": "dev@tasteos.local",
    "password": "dev123"
}

print("Testing login endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\nResponse Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    
    # Check if cookie was set
    if 'set-cookie' in response.headers:
        print(f"\n✓ Cookie set: {response.headers['set-cookie']}")
    else:
        print(f"\n✗ No cookie set in response")
        
except Exception as e:
    print(f"✗ Request failed: {e}")
    import traceback
    traceback.print_exc()
