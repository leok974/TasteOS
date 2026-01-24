"""Image generation worker with locking and retry logic.

Polls for pending recipe_images and processes them:
1. Locks row with `FOR UPDATE SKIP LOCKED` (Postgres only)
2. Sets status="processing", worker_id=self
3. Calls Gemini → WebP conversion → Upload
4. Updates active_image_id on success
5. Handles retries with exponential backoff on failure

Usage:
    python -m app.worker
"""

import hashlib
import io
import os
import time
import uuid
import traceback
from datetime import datetime, timedelta, timezone

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import select, text, func

from .db import init_engine, SessionLocal
from .models import RecipeImage, Recipe
from .settings import settings
from .ai.gemini_image import generate_image_for_recipe
from .storage.s3_compat import get_store


POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
MAX_ATTEMPTS = 3


def processing_backoff(attempt: int) -> int:
    """Exponential backoff: 30s, 60s, 120s..."""
    return 30 * (2 ** attempt)


def claim_job(db: Session) -> RecipeImage | None:
    """Claim a pending job using FOR UPDATE SKIP LOCKED.
    
    This ensures no two workers grab the same job.
    """
    try:
        # Postgres-specific locking
        # Find one pending job that is ready to run (next_attempt_at <= now or null)
        stmt = (
            select(RecipeImage)
            .filter(
                RecipeImage.status == "pending",
                (RecipeImage.next_attempt_at.is_(None)) | (RecipeImage.next_attempt_at <= func.now())
            )
            .order_by(RecipeImage.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        
        image = db.execute(stmt).scalar_one_or_none()
        
        if image:
            image.status = "processing"
            image.worker_id = WORKER_ID
            image.locked_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(image)
            print(f"[WORKER {WORKER_ID}] Claimed active job: {image.id}")
            return image
            
    except Exception as e:
        print(f"[WORKER {WORKER_ID}] Error claiming job: {e}")
        db.rollback()
    
    return None


def process_image(db: Session, image: RecipeImage) -> None:
    """Process a claimed image job."""
    print(f"[WORKER {WORKER_ID}] Processing {image.id} (Attempt {image.attempts + 1})")
    
    try:
        # Get recipe
        recipe = db.get(Recipe, image.recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {image.recipe_id} not found")
        
        # Generate image
        print(f"[WORKER {WORKER_ID}] Generating via Gemini...")
        generated = generate_image_for_recipe(
            title=recipe.title,
            cuisine=recipe.cuisines[0] if recipe.cuisines else None
        )
        
        # Convert to WebP
        print(f"[WORKER {WORKER_ID}] Converting to WebP...")
        img = Image.open(io.BytesIO(generated.png_bytes))
        webp_buffer = io.BytesIO()
        img.save(webp_buffer, format="WEBP", quality=85)
        webp_bytes = webp_buffer.getvalue()
        sha256 = hashlib.sha256(webp_bytes).hexdigest()
        
        # Upload
        store = get_store()
        storage_key = f"recipes/{recipe.id}/{image.id}.webp"
        store.put_bytes(
            key=storage_key,
            content_type="image/webp",
            data=webp_bytes,
        )
        
        # Success update
        image.status = "ready"
        image.storage_key = storage_key
        image.provider = "gemini"
        image.model = generated.model
        image.prompt = generated.prompt
        image.width = img.width
        image.height = img.height
        image.sha256 = sha256
        image.last_error = None
        
        # Update active image pointer
        recipe.active_image_id = image.id
        
        print(f"[WORKER {WORKER_ID}] ✓ Success! Active image set for {recipe.title}")
        
    except Exception as e:
        print(f"[WORKER {WORKER_ID}] ✗ Failed: {e}")
        traceback.print_exc()
        
        image.attempts += 1
        image.last_error = str(e)
        
        if image.attempts >= MAX_ATTEMPTS:
            image.status = "failed"
            print(f"[WORKER {WORKER_ID}] Max attempts reached. Marked failed.")
        else:
            image.status = "pending"
            backoff = processing_backoff(image.attempts)
            image.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            print(f"[WORKER {WORKER_ID}] Rescheduled for {backoff}s later")
    
    finally:
        db.commit()


def main():
    """Main worker loop."""
    print(f"[WORKER {WORKER_ID}] Starting (Poll: {POLL_INTERVAL}s)")
    print(f"[WORKER] DB: {settings.database_url}")
    
    init_engine()
    
    while True:
        try:
            with SessionLocal()() as db:
                # Keep claiming until queue empty
                while True:
                    job = claim_job(db)
                    if not job:
                        break
                    process_image(db, job)
                    
        except Exception as e:
            print(f"[WORKER {WORKER_ID}] Loop error: {e}")
            time.sleep(1)
        
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
