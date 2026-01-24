import re
from typing import List, Optional
from .parser import RecipeParser, ParsedRecipe, ParsedIngredient, ParsedStep

class RuleBasedParser(RecipeParser):
    def parse(self, text: str, hints: dict = None) -> ParsedRecipe:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        title = self._extract_title(lines)
        ingredients = self._extract_ingredients(lines)
        steps = self._extract_steps(lines)
        
        # Cleanup ingredients from steps if they overlap
        # (Simple heuristic: if a step looks exactly like an ingredient, ignore it? 
        # Actually usually sections are separated)

        return ParsedRecipe(
            title=title,
            ingredients=ingredients,
            steps=steps,
            servings=hints.get('servings') if hints else None
        )

    def _extract_title(self, lines: List[str]) -> str:
        # Assume first non-empty line is title, unless it's "Ingredients" or "Instructions"
        if not lines:
            return "Untitled Recipe"
        return lines[0] # Very naive, but better than nothing

    def _extract_ingredients(self, lines: List[str]) -> List[ParsedIngredient]:
        ingredients = []
        in_section = False
        
        # Common headers
        headers = ['ingredients', 'shopping list', 'what you need']
        
        for line in lines:
            lower = line.lower()
            # Check for header
            if any(h in lower for h in headers) and len(line) < 30:
                in_section = True
                continue
            
            # Check for next section header to stop
            if in_section:
                if any(k in lower for k in ['instruction', 'direction', 'method', 'preparation', 'steps']) and len(line) < 30:
                    break
                
                # Check if line looks like an ingredient (starts with number or bullet)
                # Regex for quantity: ^(\d+(?:[./]\d+)?)\s*([a-zA-Z]+)?\s+(.*)
                # Matches: "1 cup flour", "2.5 kg beef", "1/2 tsp salt"
                match = re.match(r'^([\d\./]+)\s*([a-zA-Z]+)?\s+(.*)', line)
                if match:
                    qty_str, unit, name = match.groups()
                    try:
                        # Handle fraction? 
                        if '/' in qty_str:
                            n, d = qty_str.split('/')
                            qty = float(n) / float(d)
                        else:
                            qty = float(qty_str)
                    except:
                        qty = None
                    
                    ingredients.append(ParsedIngredient(
                        name=name.strip(),
                        qty=qty,
                        unit=unit,
                        category="pantry" # Default
                    ))
                else:
                    # Maybe just a bullet point without qty?
                    if line.startswith(('-', '*', '•')):
                        ingredients.append(ParsedIngredient(name=line.lstrip('-*• ').strip()))
        
        return ingredients

    def _extract_steps(self, lines: List[str]) -> List[ParsedStep]:
        steps = []
        in_section = False
        
        headers = ['instruction', 'direction', 'method', 'preparation', 'steps', 'how to make']
        
        current_step_lines = []
        
        for line in lines:
            lower = line.lower()
            if any(h in lower for h in headers) and len(line) < 30:
                in_section = True
                continue
            
            if in_section:
                # Check if we hit end or notes
                if 'notes' in lower and len(line) < 10:
                    break
                
                # Detect new step (numbered or just new paragraphs?)
                # If starts with number dot: "1. Mix content"
                match = re.match(r'^(\d+)\.\s+(.*)', line)
                if match:
                    # Save previous step if exists
                    if current_step_lines:
                        steps.append(self._create_step(len(steps), current_step_lines))
                        current_step_lines = []
                    
                    steps.append(ParsedStep(
                        step_index=len(steps),
                        title=match.group(2)[:200], # Cap length for title
                        bullets=[match.group(2)]
                    ))
                else:
                    # Append to current step logic or create new if big gap?
                    # For now, let's just treat non-numbered lines as bullets of a step if we have one,
                    # or new steps if we don't have numbering.
                    if steps:
                        steps[-1].bullets.append(line)
                    else:
                        # No numbered steps yet, create generic ones?
                        steps.append(ParsedStep(
                            step_index=len(steps),
                            title=line[:50],
                            bullets=[line]
                        ))
                        
        return steps

    def _create_step(self, index: int, text_lines: List[str]) -> ParsedStep:
        title = text_lines[0][:50] if text_lines else "Step"
        return ParsedStep(
            step_index=index,
            title=title,
            bullets=text_lines
        )
