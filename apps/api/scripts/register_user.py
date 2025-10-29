#!/usr/bin/env python3
"""
Quick script to register a test user via the API.

Usage:
    python scripts/register_user.py

This will register a user with:
    Email: dev@tasteos.local
    Password: dev123
    Name: Dev User
"""

import requests
import sys

API_BASE = "http://localhost:8000"

def register_user():
    """Register a test user via the /api/v1/auth/register endpoint."""
    url = f"{API_BASE}/api/v1/auth/register"

    payload = {
        "email": "dev@tasteos.local",
        "password": "dev123",
        "name": "Dev User",
        "is_active": True,
        "plan": "free"
    }

    print("Registering user...")
    print(f"Email: {payload['email']}")
    print(f"Password: {payload['password']}")
    print()

    try:
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            user = response.json()
            print("✓ User registered successfully!")
            print()
            print(f"User ID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Name: {user['name']}")
            print()
            print("You can now login at http://localhost:5173/login")
            return 0
        elif response.status_code == 400:
            error = response.json()
            if "already registered" in error.get("detail", ""):
                print("✓ User already exists! You can login with:")
                print(f"   Email: {payload['email']}")
                print(f"   Password: {payload['password']}")
                print()
                print("Go to http://localhost:5173/login")
                return 0
            else:
                print(f"✗ Registration failed: {error.get('detail', 'Unknown error')}")
                return 1
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            return 1

    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to API server at http://localhost:8000")
        print("  Make sure the backend is running:")
        print("  Run the 'tasteos-api' task in VS Code")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(register_user())
