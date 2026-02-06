import json
import logging
from typing import Optional, Dict, Any

from ..schemas import InsightsResponse, InsightPattern, InsightPlaybookItem, InsightMethodTip, InsightNextFocus
from ..core.ai_client import ai_client

logger = logging.getLogger("tasteos.insights")

class InsightsGenerator:
    def __init__(self):
        pass

    async def generate_with_ai(self, facts: Dict[str, Any], style: str) -> Optional[InsightsResponse]:
        """
        Calls Gemini to generate insights from facts.
        Returns None if AI fails or is disabled (or mock mode triggers fake response).
        """
        # 1. Mock Mode Check (Delegated to Client check or explicit here if we want forced mock content)
        # The AIClient returns None if mode is mock.
        # But here we want a specific mock response for insights.
        if ai_client.mode == "mock":
             return self._get_mock_ai_response()

        # 2. Check Availability
        if not ai_client.is_available():
            logger.warning("AI client not available, skipping AI insights.")
            return None
            
        try:
            prompt = self._build_prompt(facts, style)
            
            result = await ai_client.generate_structured(
                prompt=prompt,
                response_model=InsightsResponse
            )
            
            if result:
                # model_name is not returned by generate_structured directly in result, 
                # but we can set it if we want, or leave default.
                # result is a Pydantic model (InsightsResponse)
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"AI Insights generation failed: {e}")
            return None

    def generate_heuristic_fallback(self, facts: Dict[str, Any]) -> InsightsResponse:
        """
        Deterministic, rule-based generation when AI fails.
        """
        counts = facts.get("counts", {})
        methods = counts.get("methods", {})
        adjustments = counts.get("adjustments", {})
        top_tags = facts.get("top_tags", [])
        
        # 1. Headline
        top_method = max(methods, key=methods.get) if methods else "Cooking"
        headline = f"Patterns from your recent {top_method.replace('_', ' ')} sessions"
        
        # 2. Patterns
        patterns = []
        # Top adjustment pattern
        if adjustments:
            top_adj = max(adjustments, key=adjustments.get)
            count = adjustments[top_adj]
            patterns.append(InsightPattern(
                title=f"Frequent Adjustment: {top_adj.replace('_', ' ')}",
                evidence=[f"Recorded {count} times in the last {facts['window_days']} days"],
                confidence=0.6, # Low confidence for heuristic
                tags=[top_adj]
            ))
            
        # 3. Next Focus
        next_focus = []
        if adjustments:
             top_adj = max(adjustments, key=adjustments.get)
             next_focus.append(InsightNextFocus(
                 goal=f"Reduce instances of {top_adj.replace('_', ' ')}",
                 why="It is your most frequent correction.",
                 action="Check ingredients/heat earlier in the process."
             ))
        else:
            next_focus.append(InsightNextFocus(
                 goal="Explore new methods",
                 why="You have mastered your current rotation.",
                 action="Try a new technique next session."
             ))

        return InsightsResponse(
            headline=headline,
            patterns=patterns,
            playbook=[
                InsightPlaybookItem(when="General", do=["Taste as you go"], avoid=["Relying solely on timers"])
            ],
            method_tips=[],
            next_focus=next_focus,
            model="heuristic-fallback"
        )

    def _get_mock_ai_response(self) -> InsightsResponse:
         return InsightsResponse(
            headline="[AI MOCK] You are mastering the Air Fryer",
            patterns=[
                InsightPattern(
                    title="Consistency is improving",
                    evidence=["Fewer 'undercooked' tags in last 3 sessions"],
                    confidence=0.9,
                    tags=["air_fryer"]
                )
            ],
            playbook=[],
            method_tips=[],
            next_focus=[],
            model="mock-ai"
        )

    def _build_prompt(self, facts: Dict[str, Any], style: str) -> str:
        return f"""
You are a cooking coach. Analyze these cooking facts and output a JSON response.
Style: {style} (Coach: encouraging but direct. Concise: bullet points. Chef: technical).

FACTS:
{json.dumps(facts, indent=2)}

OUTPUT SCHEMA (JSON):
{{
  "headline": "string",
  "patterns": [
    {{ "title":"string", "evidence":["string"], "confidence":0.0-1.0, "tags":["tag"] }}
  ],
  "playbook": [
    {{ "when":"situation/tag", "do":["action"], "avoid":["action"] }}
  ],
  "method_tips": [
    {{ "method":"method_name", "tips":["tip"], "common_pitfalls":["pitfall"] }}
  ],
  "next_focus": [
    {{ "goal":"string", "why":"string", "action":"string" }}
  ]
}}

Provide specific, actionable advice based ONLY on the provided facts/examples.
"""
