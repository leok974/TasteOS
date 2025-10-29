import requests
import json

url = "http://localhost:8000/api/v1/auth/register"
payload = {
    "email": "test2@example.com",
    "password": "test123",
    "name": "Test User",
    "is_active": True,
    "plan": "free"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()
