"""
Variant Generator Agent using LangGraph.

This agent generates recipe variants based on user preferences,
dietary restrictions, and available ingredients.
"""

from typing import Annotated, Any, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from tasteos_api.core.config import get_settings


class VariantState(TypedDict):
    """State for variant generation workflow."""

    messages: Annotated[list[BaseMessage], add_messages]
    recipe_id: UUID
    original_recipe: dict[str, Any]
    variant_type: str
    user_preferences: dict[str, Any]
    generated_variant: dict[str, Any] | None
    changes: list[dict[str, Any]]
    confidence_score: float


class VariantGeneratorAgent:
    """LangGraph agent for generating recipe variants."""

    def __init__(self):
        """Initialize the variant generator agent."""
        settings = get_settings()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for variant generation."""
        workflow = StateGraph(VariantState)

        # Add nodes
        workflow.add_node("analyze_recipe", self._analyze_recipe)
        workflow.add_node("generate_changes", self._generate_changes)
        workflow.add_node("apply_changes", self._apply_changes)
        workflow.add_node("validate_variant", self._validate_variant)

        # Define edges
        workflow.set_entry_point("analyze_recipe")
        workflow.add_edge("analyze_recipe", "generate_changes")
        workflow.add_edge("generate_changes", "apply_changes")
        workflow.add_edge("apply_changes", "validate_variant")
        workflow.add_edge("validate_variant", END)

        return workflow.compile()

    async def _analyze_recipe(self, state: VariantState) -> VariantState:
        """Analyze the original recipe structure and content."""
        recipe = state["original_recipe"]
        variant_type = state["variant_type"]
        preferences = state["user_preferences"]

        prompt = f"""Analyze this recipe for {variant_type} modification:

Recipe: {recipe.get('title')}
Description: {recipe.get('description')}
Cuisine: {recipe.get('cuisine')}
Difficulty: {recipe.get('difficulty')}
Ingredients: {len(recipe.get('ingredients', []))} items
Instructions: {len(recipe.get('instructions', []))} steps

Variant Type: {variant_type}
User Preferences: {preferences}

Provide a brief analysis of what modifications would be most appropriate.
"""

        response = await self.llm.ainvoke(prompt)
        state["messages"].append(response)
        return state

    async def _generate_changes(self, state: VariantState) -> VariantState:
        """Generate specific changes to create the variant."""
        recipe = state["original_recipe"]
        variant_type = state["variant_type"]
        preferences = state["user_preferences"]

        # Build detailed prompt based on variant type
        prompt = self._build_variant_prompt(recipe, variant_type, preferences)

        response = await self.llm.ainvoke(prompt)

        # Parse the response to extract changes
        changes = self._parse_changes(response.content, recipe)
        state["changes"] = changes
        state["messages"].append(response)

        return state

    def _build_variant_prompt(
        self,
        recipe: dict[str, Any],
        variant_type: str,
        preferences: dict[str, Any]
    ) -> str:
        """Build a detailed prompt for variant generation."""
        base_prompt = f"""Generate a {variant_type} variant of this recipe:

**Original Recipe: {recipe.get('title')}**

Ingredients:
"""
        for ing in recipe.get('ingredients', []):
            base_prompt += f"- {ing.get('amount', '')} {ing.get('item', '')} {ing.get('notes', '')}\n"

        base_prompt += "\nInstructions:\n"
        for inst in recipe.get('instructions', []):
            base_prompt += f"{inst.get('step', '')}. {inst.get('text', '')}\n"

        base_prompt += f"\n**Variant Type: {variant_type}**\n"

        if variant_type == "dietary":
            dietary_type = preferences.get("dietary_restriction", "")
            base_prompt += f"""
Create a {dietary_type} version of this recipe.
- Replace any incompatible ingredients
- Adjust cooking methods if needed
- Maintain similar flavor profile
- Note any texture or taste differences
"""
        elif variant_type == "cuisine":
            target_cuisine = preferences.get("target_cuisine", "")
            base_prompt += f"""
Adapt this recipe to {target_cuisine} cuisine.
- Use authentic {target_cuisine} ingredients and techniques
- Maintain the core concept of the dish
- Adjust seasonings and spices appropriately
- Suggest traditional accompaniments
"""
        elif variant_type == "ingredient_substitution":
            substitutions = preferences.get("substitutions", {})
            base_prompt += f"""
Modify this recipe with these ingredient substitutions: {substitutions}
- Replace specified ingredients
- Adjust quantities proportionally
- Modify cooking times/temps if needed
- Note any flavor or texture changes
"""
        elif variant_type == "simplify":
            base_prompt += """
Simplify this recipe for easier preparation.
- Reduce number of steps where possible
- Suggest store-bought alternatives for complex components
- Minimize special equipment needs
- Maintain good results with less effort
"""
        elif variant_type == "upscale":
            base_prompt += """
Create an elevated version of this recipe.
- Suggest premium ingredient alternatives
- Add refined techniques
- Include plating suggestions
- Enhance complexity while maintaining core dish
"""

        base_prompt += """

Provide your response in this format:

CHANGES:
- [Type: ingredient] Original: <item>, New: <item>, Reason: <reason>
- [Type: instruction] Step: <step_num>, Change: <description>
- [Type: technique] Change: <description>

TITLE: <new_title>
DESCRIPTION: <new_description>
CONFIDENCE: <0-100>
"""

        return base_prompt

    def _parse_changes(self, response: str, original_recipe: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse AI response to extract structured changes."""
        changes = []
        lines = response.split('\n')

        in_changes_section = False
        for line in lines:
            line = line.strip()

            if line.startswith('CHANGES:'):
                in_changes_section = True
                continue

            if line.startswith('TITLE:') or line.startswith('DESCRIPTION:') or line.startswith('CONFIDENCE:'):
                in_changes_section = False

            if in_changes_section and line.startswith('- [Type:'):
                # Parse change line
                try:
                    # Extract type
                    type_start = line.find('[Type:') + 6
                    type_end = line.find(']', type_start)
                    change_type = line[type_start:type_end].strip()

                    # Extract details based on type
                    if change_type == "ingredient":
                        original = self._extract_field(line, "Original:")
                        new = self._extract_field(line, "New:")
                        reason = self._extract_field(line, "Reason:")

                        changes.append({
                            "type": "ingredient",
                            "original": original,
                            "new": new,
                            "reason": reason
                        })

                    elif change_type == "instruction":
                        step = self._extract_field(line, "Step:")
                        change = self._extract_field(line, "Change:")

                        changes.append({
                            "type": "instruction",
                            "step": int(step) if step.isdigit() else None,
                            "change": change
                        })

                    elif change_type == "technique":
                        change = self._extract_field(line, "Change:")

                        changes.append({
                            "type": "technique",
                            "change": change
                        })

                except Exception as e:
                    # Skip malformed change lines
                    continue

        return changes

    def _extract_field(self, line: str, field: str) -> str:
        """Extract a field value from a change line."""
        start = line.find(field)
        if start == -1:
            return ""

        start += len(field)

        # Find next field or end of line
        next_fields = ["Original:", "New:", "Reason:", "Step:", "Change:"]
        end = len(line)
        for next_field in next_fields:
            if next_field == field:
                continue
            pos = line.find(next_field, start)
            if pos != -1 and pos < end:
                end = pos

        return line[start:end].strip().rstrip(',')

    async def _apply_changes(self, state: VariantState) -> VariantState:
        """Apply the generated changes to create the variant recipe."""
        original = state["original_recipe"]
        changes = state["changes"]

        # Deep copy original recipe
        variant = {
            "title": original.get("title"),
            "description": original.get("description"),
            "servings": original.get("servings"),
            "prep_time": original.get("prep_time"),
            "cook_time": original.get("cook_time"),
            "difficulty": original.get("difficulty"),
            "cuisine": original.get("cuisine"),
            "tags": original.get("tags", []).copy(),
            "ingredients": [ing.copy() for ing in original.get("ingredients", [])],
            "instructions": [inst.copy() for inst in original.get("instructions", [])]
        }

        # Apply each change
        for change in changes:
            if change["type"] == "ingredient":
                # Find and replace ingredient
                for i, ing in enumerate(variant["ingredients"]):
                    if change["original"].lower() in ing.get("item", "").lower():
                        variant["ingredients"][i] = {
                            "item": change["new"],
                            "amount": ing.get("amount"),
                            "notes": f"{ing.get('notes', '')} (substituted from {change['original']})"
                        }

            elif change["type"] == "instruction" and change.get("step"):
                # Modify instruction step
                step_idx = change["step"] - 1
                if 0 <= step_idx < len(variant["instructions"]):
                    original_text = variant["instructions"][step_idx].get("text", "")
                    variant["instructions"][step_idx]["text"] = f"{original_text} {change['change']}"

        state["generated_variant"] = variant
        return state

    async def _validate_variant(self, state: VariantState) -> VariantState:
        """Validate the generated variant for quality and coherence."""
        variant = state["generated_variant"]
        original = state["original_recipe"]

        prompt = f"""Validate this recipe variant:

Original: {original.get('title')}
Variant: {variant.get('title')}

Check for:
1. Ingredient compatibility and quantities
2. Instruction coherence and completeness
3. Cooking times and temperatures
4. Overall feasibility

Rate confidence (0-100) and note any issues.
"""

        response = await self.llm.ainvoke(prompt)

        # Extract confidence score
        confidence = 0.75  # Default
        if "confidence:" in response.content.lower():
            try:
                conf_line = [l for l in response.content.split('\n') if 'confidence:' in l.lower()][0]
                conf_str = ''.join(filter(str.isdigit, conf_line))
                confidence = int(conf_str) / 100.0
            except:
                pass

        state["confidence_score"] = confidence
        state["messages"].append(response)

        return state

    async def generate_variant(
        self,
        recipe_id: UUID,
        recipe: dict[str, Any],
        variant_type: str,
        preferences: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate a recipe variant.

        Args:
            recipe_id: UUID of the original recipe
            recipe: Original recipe data
            variant_type: Type of variant (dietary, cuisine, etc.)
            preferences: User preferences for the variant

        Returns:
            Dictionary containing the generated variant and metadata
        """
        if preferences is None:
            preferences = {}

        # Initialize state
        initial_state: VariantState = {
            "messages": [],
            "recipe_id": recipe_id,
            "original_recipe": recipe,
            "variant_type": variant_type,
            "user_preferences": preferences,
            "generated_variant": None,
            "changes": [],
            "confidence_score": 0.0
        }

        # Run the workflow
        result = await self.graph.ainvoke(initial_state)

        return {
            "variant": result["generated_variant"],
            "changes": result["changes"],
            "confidence_score": result["confidence_score"],
            "metadata": {
                "variant_type": variant_type,
                "preferences": preferences,
                "message_count": len(result["messages"])
            }
        }
