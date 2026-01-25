
import copy
from typing import Optional
from ..models import Recipe
from ..schemas import RecipeStepOut, MethodPreviewResponse

class VariantGenerator:
    """Generates cooking method variants (e.g. Air Fryer, Instant Pot) from base recipes."""

    SUPPORTED_METHODS = {
        "air_fryer": {
            "label": "Air Fryer",
            "summary": "Crispier texture, faster cooking time (~20% less).",
            "warnings": ["Ensure basket isn't overcrowded", "Shake basket halfway through"]
        },
        "instant_pot": {
            "label": "Instant Pot",
            "summary": "Speedy pressure cooking for braises/stews.",
            "warnings": ["Requires liquid (min 1 cup)", "Natural release for meats recommended"]
        },
        "slow_cooker": {
            "label": "Slow Cooker",
            "summary": "Low and slow for tenderizing tough cuts.",
            "warnings": ["Plan for 4-8 hours cooking time"]
        }
    }

    def get_supported_methods(self):
        return [
            {"key": k, **v} for k, v in self.SUPPORTED_METHODS.items()
        ]

    def generate(self, recipe: Recipe, method_key: str) -> MethodPreviewResponse:
        """Generate a variant for the given recipe and method."""
        if method_key not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported method: {method_key}")

        # Deep copy steps to avoid mutating original (though we work with dicts usually)
        # We need to return a structure that matches valid steps
        
        # Simple Rule-Based Logic
        # In a real system, this would use LLMs or more complex parsing.
        # Here we apply heuristic templates.
        
        new_steps = []
        tradeoffs = {
            "time_delta_min": 0,
            "effort": "medium",
            "cleanup": "low", 
            "texture_notes": [],
            "risks": []
        }

        # --- Logic ---
        
        if method_key == "air_fryer":
            # Heuristic: Cut time by 20%
            time_reduction = 0
            if recipe.time_minutes:
                time_reduction = int(recipe.time_minutes * 0.2)
                tradeoffs["time_delta_min"] = -time_reduction
            
            tradeoffs["texture_notes"].append("Crispy exterior")
            tradeoffs["cleanup"] = "low"
            
            # Step transformation
            # 1. Prep remains same
            # 2. Cook steps replaced by Air Fry instructions
            
            # Simple MVP implementation: 
            # Detect "bake" or "fry" keywords? 
            # For now, append a generic Air Fry step at the end or replace the main cook step?
            # Safest MVP: Keep prep, Replace middle processing with Air Fry generic.
            
            non_cook_keywords = ["chop", "slice", "mix", "marinate", "prep", "preheat"]
            
            for step in recipe.steps:
                is_prep = any(k in step.title.lower() for k in non_cook_keywords)
                
                if is_prep:
                    new_steps.append({
                        "id": f"var-{step.id}", # distinct ID
                        "step_index": len(new_steps),
                        "title": step.title,
                        "bullets": step.bullets,
                        "minutes_est": step.minutes_est
                    })
                else:
                    # Assumed cooking step - modify
                    original_mins = step.minutes_est or 15
                    new_mins = max(1, int(original_mins * 0.8))
                    
                    new_steps.append({
                        "id": f"var-{step.id}",
                        "step_index": len(new_steps),
                        "title": f"Air Fry: {step.title}",
                        "bullets": [
                            f"Preheat Air Fryer to 375°F (190°C) if needed.",
                            f"Arrange food in single layer in basket (do not overcrowd).",
                            f"Cook for {new_mins} minutes, shaking basket halfway through."
                        ],
                        "minutes_est": new_mins
                    })
                    
        elif method_key == "instant_pot":
            tradeoffs["time_delta_min"] = -15 # Generic saving
            tradeoffs["texture_notes"].append("Tender, braised texture")
            tradeoffs["effort"] = "low"
            
            new_steps.append({
                "id": "var-ip-sante",
                "step_index": 0,
                "title": "Sauté Aromatics",
                "bullets": ["Set Instant Pot to 'Sauté' mode.", "Add oil and aromatics (onions, garlic) if recipe calls for them.", "Cook until softened."],
                "minutes_est": 5
            })
            
            new_steps.append({
                "id": "var-ip-pressure",
                "step_index": 1,
                "title": "Pressure Cook",
                "bullets": ["Add remaining ingredients and at least 1 cup of liquid.", "Secure lid and set to High Pressure.", "Cook for 2/3 of original time."],
                "minutes_est": 20
            })
            
            new_steps.append({
                "id": "var-ip-release",
                "step_index": 2,
                "title": "Natural Release",
                "bullets": ["Allow natural release for 10 minutes, then quick release remaining pressure."],
                "minutes_est": 10
            })

        else:
            # Fallback
            new_steps = [
                {
                    "id": f"var-{s.id}", "step_index": i, "title": s.title, "bullets": s.bullets, "minutes_est": s.minutes_est
                } for i, s in enumerate(recipe.steps)
            ]

        return MethodPreviewResponse(
            tradeoffs=tradeoffs,
            steps_preview=new_steps,
            diff=None # Frontend can calculate diff or we do it here? MVP: Frontend or None
        )

variant_generator = VariantGenerator()
