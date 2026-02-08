import re

def clean_md(text: str) -> str:
    """
    Sanitize markdown artifacts from text.
    Removes:
    - Leading headers (#, ##)
    - Bold markers (**, __)
    - Leading bullets (-, *)
    """
    if not text:
        return ""
    
    # Remove bolding (**text** -> text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    
    # Remove leading headers (# Title -> Title)
    text = re.sub(r"^\s*#+\s+", "", text)
    
    # Remove leading bullets (- Item -> Item)
    text = re.sub(r"^\s*[-*]\s+", "", text)
    
    return text.strip()

def _clamp(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length-1].rstrip() + "…"

def _normalize_bullet(text: str) -> str:
    return re.sub(r"^\s*[-•*]\s+", "", text).strip()

def _split_compound_bullets(text: str) -> list[str]:
    # Split by strong separators: semicolon, or period followed by space
    parts = [p.strip() for p in re.split(r';\s+|\.\s+', text) if p.strip()]
    
    # If explicit split didn't do much, try " then " or " and " if it's long?
    # Keeping it simple for now to match safety of TS logic
    return parts

def parse_step_text(raw_text: str) -> dict:
    """
    Parses a raw step text into {title, bullets}.
    Mimics the frontend 'toStructuredStep' logic for consistent saving.
    """
    s = (raw_text or "").strip()
    s = clean_md(s) # Ensure clean before splitting
    if not s:
        return {"title": "", "bullets": []}

    # 1. Newline split
    if "\n" in s:
        lines = [x.strip() for x in s.split("\n") if x.strip()]
        if not lines:
             return {"title": "", "bullets": []}
        
        # First line is title, rest are bullets
        title = _clamp(lines[0], 45)
        # Normalize bullets and flatten
        bullets = []
        for line in lines[1:]:
             normalized = _normalize_bullet(line)
             # Optional: Split compound bullets if they are long?
             # For now, just add them
             bullets.append(normalized)
             
        return {
            "title": title,
            "bullets": bullets
        }

    # 2. Colon split "Title: Description"
    colon_idx = s.find(":")
    if 0 < colon_idx < 60:
        left = s[:colon_idx].strip()
        right = s[colon_idx+1:].strip()
        
        bullets = []
        if right:
             # Split the description into multiple bullets if apt
             bullets = _split_compound_bullets(right)
             # Fallback if split failed to produce list (e.g. one short sentence)
             if not bullets: 
                 bullets = [right]
        
        return {
            "title": _clamp(left, 45),
            "bullets": bullets
        }

    # 3. Long paragraph split
    if len(s) > 100:
        # Split by sentence boundary
        parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', s) if p.strip()]
        if not parts:
             return {"title": _clamp(s, 45), "bullets": []}
             
        first = parts[0]
        rest = parts[1:]
        
        # If we have no rest, but the first is huge, we might have failed either way.
        # But assuming first sentence is the "Main Idea".
        
        # If rest is empty, but first was huge, we just clamped it.
        # Maybe we iterate through 'rest' and split further?
        
        bullets = []
        for r in rest:
            bullets.extend(_split_compound_bullets(r))
            
        return {
            "title": _clamp(first, 45),
            "bullets": bullets
        }

    # 4. Short enough to be just a title
    return {"title": _clamp(s, 45), "bullets": []}


def normalize_step_structure(title: str, bullets: list[str]) -> dict:
    """
    Enforce strict structure on step data:
    - Short title (2-6 words approx)
    - 2-5 bullets (split if necessary)
    - No redundancy
    """
    # 0. Clean inputs
    title = clean_md(title or "")
    bullets = [clean_md(b) for b in (bullets or []) if clean_md(b)]

    # 1. Title Normalization
    # Rules: Title must be short label-like.
    # Bad if: > 28 chars, contains period, ends in punctuation, or looks like sentence start.
    
    bad_prefixes = ("In a ", "Add the ", "Heat ", "Combine ", "Mix ", "Place ", "To make ")
    is_long = len(title) > 25
    has_period = "." in title
    is_sentence_like = title.startswith(bad_prefixes) and len(title) > 20
    is_too_many_words = len(title.split()) > 5

    if is_long or has_period or is_sentence_like or is_too_many_words:
        # Move original title to bullets if it has meaningful content
        # (avoid moving "Prep" or "Step 1" if it's just that)
        if len(title) > 10:
             bullets.insert(0, title)
        
        # Generate Short Label
        # Heuristic 1: Split by colon if present "Make the sauce: Combine..."
        if ":" in title:
            candidate = title.split(":")[0].strip()
            if len(candidate) < 25:
                title = candidate
            else:
                title = _extract_short_verb_label(title)
        else:
            title = _extract_short_verb_label(title)

    # 2. Bullet Splitting & Enrichment
    # If bullets empty or looking sparse/long, normalize them
    if not bullets or (len(bullets) == 1 and len(bullets[0]) > 20):
        # We need to manufacture a list
        source = bullets[0] if bullets else ""
        if not source:
             # If completely empty, we have a problem. 
             # Refill from title if we stripped it? But we already moved title to bullets[0] above.
             pass
        
        # Aggressive splitting
        new_bullets = []
        to_process = bullets if bullets else []
        
        for item in to_process:
            # simple split by punctuation
            # Split on: . ; | then | and then | until 
            split_pattern = r'[.;]\s+|\s+then\s+|\s+and then\s+|\s+until\s+|\s+,\s+then\s+'
            parts = re.split(split_pattern, item, flags=re.IGNORECASE)
            
            for p in parts:
                p = p.strip()
                if p:
                    # Further clamp if still huge?
                    new_bullets.append(p)
        
        bullets = new_bullets

    # 3. Deduplicate and Validation
    final_bullets = []
    
    def _norm(t): return t.lower().strip().strip(".,;:").replace("  ", " ")
    
    norm_title = _norm(title)
    
    for b in bullets:
        norm_b = _norm(b)
        if not norm_b: continue
        
        # Dedupe against title
        if norm_b == norm_title:
            continue
            
        # Dedupe if bullet starts with title (redundant repitition)
        # ONLY if the title looks like a complete label (e.g. ended with :)
        # Otherwise we risk stripping the verb from "Form the beef" -> "The beef"
        # For now, let's overlap to be safe, unless it's an exact match handled above.
        # But if we have "Prep: Prep the onion", we want to strip.
        if ":" in title or len(title) < 10:
             if norm_b.startswith(norm_title) and len(norm_b) > len(norm_title):
                stripped = b[len(title):].strip(" .,-:")
                if stripped and len(stripped) > 3:
                     final_bullets.append(stripped.capitalize())
                     continue

        # Dedupe against existing
        if any(_norm(fb) == norm_b for fb in final_bullets):
            continue
            
        final_bullets.append(b)
    
    # Safety: Ensure at least one bullet
    if not final_bullets:
        final_bullets = ["Follow the step above"] # Fallback if we stripped everything

    return {
        "title": title,
        "bullets": final_bullets
    }

def _extract_short_verb_label(text: str) -> str:
    """Attempt to pull a 2-4 word label from a longer sentence."""
    words = text.split()
    if not words:
        return "Prep"
    
    # Heuristic: Skip 'the', 'a', 'an', 'in' for the Label, but keep the first word (usually verb)
    clean_words = []
    if words:
        clean_words.append(words[0])
        for w in words[1:]:
            if w.lower() not in ("the", "a", "an", "in", "to", "of", "with"):
                clean_words.append(w)
            if len(clean_words) >= 3:
                break
    
    if not clean_words:
        return "Step"

    candidate = " ".join(clean_words)
    # Strip punctuation
    candidate = re.sub(r"[.,;:]+$", "", candidate)
    
    # If still too long (e.g. very long words), clamp
    if len(candidate) > 25:
         candidate = candidate[:22] + "..."
        
    return candidate

