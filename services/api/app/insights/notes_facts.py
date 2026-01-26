from typing import Any, Dict, List, Optional
import hashlib
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, text, or_

from ..models import RecipeNoteEntry, CookSession, Recipe
from ..settings import settings

class NotesFactsBuilder:
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id

    def build_facts(
        self, 
        recipe_id: Optional[str] = None, 
        window_days: int = 90, 
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Aggregates raw note entries into a structured 'facts' object 
        suitable for LLM consumption.
        """
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        
        # 1. Query Notes
        query = (
            select(RecipeNoteEntry)
            .where(
                RecipeNoteEntry.workspace_id == self.workspace_id,
                RecipeNoteEntry.created_at >= since,
                RecipeNoteEntry.deleted_at.is_(None)
            )
            .order_by(desc(RecipeNoteEntry.created_at))
            .limit(limit)
        )
        
        if recipe_id:
            query = query.where(RecipeNoteEntry.recipe_id == recipe_id)
            
        entries = self.db.scalars(query).all()
        
        # 2. Aggregations
        method_counts = {}
        adjustment_counts = {}
        source_counts = {}
        all_tags = []
        
        # Known categories for heuristic classification
        known_methods = [
            "air_fryer", "instant_pot", "wok", "dutch_oven", 
            "cast_iron", "steamer", "sous_vide", "slow_cooker",
            "pressure_cooker", "oven", "stovetop", "grill"
        ]
        
        known_adjustments = [
            "too_thick", "too_thin", "too_salty", "too_spicy", 
            "burning", "no_browning", "undercooked", "overcooked", 
            "bland", "dry", "wet", "bitter", "sour", "sweet"
        ]

        examples = []
        
        for entry in entries:
            # Sources
            src = entry.source or "unknown"
            source_counts[src] = source_counts.get(src, 0) + 1
            
            # Tags processing
            entry_tags = entry.tags or []
            for t in entry_tags:
                all_tags.append(t)
                
                # classify
                if t in known_methods:
                    method_counts[t] = method_counts.get(t, 0) + 1
                elif t in known_adjustments:
                    adjustment_counts[t] = adjustment_counts.get(t, 0) + 1
            
            # Capture small examples (first 5-10)
            if len(examples) < 8:
                examples.append({
                    "date": entry.created_at.strftime("%Y-%m-%d"),
                    "title": entry.title,
                    "tags": entry_tags,
                    "excerpt": (entry.content_md or "")[:200].replace("\n", " ").strip()
                })

        # 3. Simple Phrase Extraction (Heuristic N-gram / Keyword)
        # This is very basic; purely to give the LLM hints about recurring text patterns
        # beyond just tags.
        phrases = self._extract_common_phrases([e.content_md for e in entries if e.content_md])

        # 4. Co-occurrence (Pairs of tags)
        co_occurrence = self._calculate_co_occurrence([e.tags for e in entries if e.tags])

        # 5. Top Tags
        from collections import Counter
        tag_counts = Counter(all_tags)
        top_tags = [t for t, _ in tag_counts.most_common(10)]

        facts = {
            "scope": "recipe" if recipe_id else "workspace",
            "window_days": window_days,
            "counts": {
                "entries": len(entries),
                "methods": method_counts,
                "adjustments": adjustment_counts,
                "sources": source_counts
            },
            "top_tags": top_tags,
            "co_occurrence": co_occurrence,
            "top_phrases": phrases,
            "examples": examples
        }
        
        return facts

    def _calculate_co_occurrence(self, tags_list_of_lists: List[List[str]]) -> List[Dict]:
        """Finds pairs of tags that appear together often."""
        pair_counts = {}
        for tags in tags_list_of_lists:
            # Sort to ensure (a,b) is same as (b,a)
            sorted_tags = sorted(list(set(tags)))
            for i in range(len(sorted_tags)):
                for j in range(i + 1, len(sorted_tags)):
                    pair = (sorted_tags[i], sorted_tags[j])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
        
        # Filter for relevant ones (>1)
        results = []
        for (a, b), count in pair_counts.items():
            if count > 1:
                results.append({"a": a, "b": b, "count": count})
        
        # Sort by count desc
        results.sort(key=lambda x: x["count"], reverse=True)
        return results[:10]

    def _extract_common_phrases(self, texts: List[str]) -> List[Dict]:
        """
        Very crude phrase extractor. 
        Splits by common delimiters, normalizes, counts exact matches (>2 occurrences).
        """
        phrase_counter = {}
        
        for text in texts:
            if not text: continue
            # Split by newlines, periods, bullet points
            import re
            parts = re.split(r'[\n\.\-\*]', text)
            for p in parts:
                clean = p.strip().lower()
                # Filter out very short or very long junk
                if len(clean) < 10 or len(clean) > 80:
                    continue
                phrase_counter[clean] = phrase_counter.get(clean, 0) + 1
        
        results = []
        for p, count in phrase_counter.items():
            if count >= 2:
                results.append({"phrase": p, "count": count})
        
        results.sort(key=lambda x: x["count"], reverse=True)
        return results[:5]

    def hash_facts(self, facts: Dict) -> str:
        """Create a deterministic hash of the facts dictionary to use as cache key."""
        # Sort keys to ensure consistent JSON str
        s = json.dumps(facts, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
