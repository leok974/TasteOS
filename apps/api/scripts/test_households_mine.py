"""
Test the /households/mine endpoint with authentication.
"""
import requests
import json

# First login to get a token
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "dev@tasteos.local", "password": "dev123"},
    headers={"Content-Type": "application/json"}
)

print("Login Status:", login_response.status_code)

if login_response.status_code == 200:
    data = login_response.json()
    token = data.get("access_token")
    print(f"✓ Got token: {token[:50]}...")

    # Get cookies from login
    cookies = login_response.cookies

    # Test /households/mine with cookie
    print("\n--- Testing /households/mine with cookie ---")
    households_response = requests.get(
        "http://localhost:8000/api/v1/households/mine",
        cookies=cookies
    )

    print(f"Status: {households_response.status_code}")
    print(f"Response: {json.dumps(households_response.json(), indent=2)}")

    # Also test with Bearer token
    print("\n--- Testing /households/mine with Bearer token ---")
    households_response2 = requests.get(
        "http://localhost:8000/api/v1/households/mine",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"Status: {households_response2.status_code}")
    print(f"Response: {json.dumps(households_response2.json(), indent=2)}")
else:
    print("Login failed!")
    print(login_response.text)
