import sys
import os

# We are in services/api
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("App imported successfully")
    
    # Check routes
    found = False
    for route in app.routes:
        if hasattr(route, "path") and "adjust/preview" in route.path:
            print(f"Found route: {route.path}")
            found = True
    
    if not found:
        print("ERROR: Route adjust/preview NOT FOUND")
        # Print all routes for debug
        for route in app.routes:
             if hasattr(route, "path"):
                 print(f"  Existing: {route.path}")
        sys.exit(1)
        
except Exception as e:
    print(f"App import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
