import sys
import os
import re
from datetime import datetime

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import SessionLocal
from app.models import Recipe, RecipeNoteEntry

def parse_and_migrate(db, recipe_id=None):
    query = db.query(Recipe)
    if recipe_id:
        query = query.filter(Recipe.id == recipe_id)
        
    recipes = query.all()
    print(f"Checking {len(recipes)} recipes for legacy notes...")
    
    migrated_count = 0
    
    for recipe in recipes:
        if not recipe.notes:
            continue
            
        full_text = recipe.notes
        # Split by the separator pattern used in cook.py
        # Pattern: "\n\n---\n{Title}\n{Body}"
        # Where title usually starts with "Cook Session"
        
        # Regex to find the separator
        # We look for \n---\n
        parts = re.split(r'\n+---\n+', full_text)
        
        # The first part might be just generic notes before any session
        base_note = parts[0].strip()
        
        entries_to_create = []
        
        # Migrate base note if it exists
        if base_note:
            # Check for existing "General Notes" or similar
            # Use title "General Notes" or "Recipe Notes"
            base_title = "General Notes"
            
            exists_base = db.query(RecipeNoteEntry).filter(
                RecipeNoteEntry.recipe_id == recipe.id,
                RecipeNoteEntry.title == base_title,
                RecipeNoteEntry.deleted_at.is_(None)
            ).first()
            
            if not exists_base:
                entry = RecipeNoteEntry(
                    id=str(uuid.uuid4()),
                    workspace_id=recipe.workspace_id,
                    recipe_id=recipe.id,
                    source="migration",
                    title=base_title,
                    content_md=base_note,
                    created_at=recipe.created_at or datetime.now(), # Use recipe creation date for base notes
                    applied_to_recipe_notes=True
                )
                entries_to_create.append(entry)

        # Subsequent parts are sessions
        for part in parts[1:]:
            part = part.strip()
            if not part: continue
            
            # Extract title (first line)
            lines = part.split('\n', 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            
            # Try to extract date from title for sorting/created_at
            # Format: Cook Session (YYYY-MM-DD):
            date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', title)
            created_at = datetime.now()
            if date_match:
                try:
                    created_at = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                except:
                    pass
            
            # Check for dupe based on content hash or similar? 
            # Or just check if title+recipe_id exists?
            # Let's rely on simple title + recipe_id check for now to avoid double insertion on re-run
            # Note: This is imperfect but good enough for a one-off
            
            exists = db.query(RecipeNoteEntry).filter(
                RecipeNoteEntry.recipe_id == recipe.id,
                RecipeNoteEntry.title == title,
                RecipeNoteEntry.deleted_at.is_(None)
            ).first()
            
            if not exists:
                entry = RecipeNoteEntry(
                    id=str(uuid.uuid4()), # We need to import uuid
                    workspace_id=recipe.workspace_id,
                    recipe_id=recipe.id,
                    source="migration",
                    title=title,
                    content_md=body,
                    created_at=created_at,
                    applied_to_recipe_notes=True
                )
                entries_to_create.append(entry)
        
        if entries_to_create:
            print(f"Migrating {len(entries_to_create)} entries for recipe {recipe.title}")
            db.add_all(entries_to_create)
            migrated_count += len(entries_to_create)
            
            # Optional: Clean up legacy notes?
            # Ideally we keep them for safety as requested, but maybe we update the 'base' note?
            # recipe.notes = base_note (WARNING: DESTRUCTIVE)
            # Keeping it safe: Do NOT modify recipe.notes for now.
            
    db.commit()
    print(f"Migration complete. {migrated_count} entries created.")

if __name__ == "__main__":
    import uuid # Import here
    # SessionLocal returns the sessionmaker class/factory in this codebase structure apparently
    # Based on db.py: SessionLocal() returns _SessionLocal which IS the sessionmaker
    # So we need to instantiate it: SessionLocal()() 
    
    session_factory = SessionLocal()
    db = session_factory()
    
    try:
        # If argument provided
        target_id = sys.argv[1] if len(sys.argv) > 1 else None
        parse_and_migrate(db, target_id)
    finally:
        db.close()
