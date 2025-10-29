import sys
sys.path.insert(0, '.')

from tasteos_api.routers import auth

print("Auth module loaded successfully")
print(f"Has LoginRequest: {hasattr(auth, 'LoginRequest')}")
print(f"Login function: {auth.login}")
print(f"Login parameters: {auth.login.__code__.co_varnames[:auth.login.__code__.co_argcount]}")
