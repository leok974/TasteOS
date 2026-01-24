
import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/api"

def run():
    # 1. Seed
    print("Seeding...")
    requests.post(f"{BASE_URL}/dev/seed")
    
    # 2. Generate Plan
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    if today.weekday() > 0: # If mid-week, plan for next week? No, strictly current week for MVP
        pass
        
    print(f"Generating plan for week starting {monday}...")
    resp = requests.post(f"{BASE_URL}/plan/generate", json={"week_start": str(monday)})
    if resp.status_code != 200:
        print("Plan Gen Failed:", resp.text)
        return
        
    plan = resp.json()
    print(f"Plan ID: {plan['id']}")
    print(f"Entries: {len(plan['entries'])}")
    
    for e in plan['entries'][:4]:
        print(f" - {e['date']} {e['meal_type']}: {e['recipe_title']} ({'Leftover' if e['is_leftover'] else 'Fresh'})")
        
    # 3. Generate Grocery from Plan
    print("\nGenerating Grocery List from Plan...")
    resp = requests.post(f"{BASE_URL}/grocery/generate", json={"plan_id": plan['id']})
    if resp.status_code != 200:
        print("Grocery Gen Failed:", resp.text)
        return
        
    grocery = resp.json()
    print(f"Grocery List Source: {grocery['source']}")
    print(f"Items: {len(grocery['items'])}")
    for i in grocery['items'][:3]:
        print(f" - {i['name']} ({i['status']})")

    # 4. Test Swap Recipe
    print("\nTesting Swap...")
    target_entry = plan['entries'][0]
    print(f"Original: {target_entry['recipe_title']}")
    
    # Get a random recipe to swap to (cheat: use same logic to find one via recipes endpoint if we had it, but for test, hardcode or just swap to same if logic works?)
    # Let's just assume we have another recipe.
    # Actually, we can fetch recipes first.
    recipes_resp = requests.get(f"{BASE_URL}/recipes")
    if recipes_resp.status_code == 200:
        all_recipes = recipes_resp.json()
        new_recipe = next((r for r in all_recipes if r['id'] != target_entry['recipe_id']), None)
        
        if new_recipe:
            print(f"Swapping to: {new_recipe['title']}")
            patch_resp = requests.patch(f"{BASE_URL}/plan/entries/{target_entry['id']}", json={"recipe_id": new_recipe['id'], "is_leftover": False})
            if patch_resp.status_code == 200:
                updated_entry = patch_resp.json()
                print(f"Updated: {updated_entry['recipe_title']}")
                print(f"Method: {updated_entry['method_choice']}")
            else:
                 print("Swap Failed:", patch_resp.text)
        else:
             print("No other recipe found to swap.")
    
if __name__ == "__main__":
    run()
