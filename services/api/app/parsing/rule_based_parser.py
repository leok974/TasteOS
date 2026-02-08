import re
from typing import List, Optional
from .parser import RecipeParser, ParsedRecipe, ParsedIngredient, ParsedStep

class RuleBasedParser(RecipeParser):
    def parse(self, text: str, hints: dict = None) -> ParsedRecipe:
        # 1. Normalize emojis (quick win)
        text = self._normalize_emojis(text)
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if hints and hints.get('title_hint'):
            title = hints['title_hint']
        else:
            title = self._extract_title(lines)
            
        ingredients = self._extract_ingredients(lines)
        steps = self._extract_steps(lines)
        
        return ParsedRecipe(
            title=title,
            ingredients=ingredients,
            steps=steps,
            servings=hints.get('servings') if hints else None
        )

    def _normalize_emojis(self, text: str) -> str:
        replacements = {
            '1️⃣': '1.', '2️⃣': '2.', '3️⃣': '3.', '4️⃣': '4.', '5️⃣': '5.',
            '6️⃣': '6.', '7️⃣': '7.', '8️⃣': '8.', '9️⃣': '9.', '0️⃣': '0.',
            '🔟': '10.'
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def _extract_title(self, lines: List[str]) -> str:
        # Assume first non-empty line is title, unless it's "Ingredients" or "Instructions"
        if not lines:
            return "Untitled Recipe"
        
        # Clean up markdown header syntax
        # e.g. "# Title" -> "Title"
        return lines[0].lstrip('#').strip()

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
        
        # Regex patterns for step headers
        step_patterns = [
            r'^\s*(\d{1,2})[.)]\s+(.+)$',                 # 1. or 1)
            r'^\s*(\d{1,2})\s*[-:]\s+(.+)$',              # 1 - or 1:
            r'^\s*(?i:step)\s*(\d{1,2})[:\-.)]?\s+(.+)$', # Step 1:
        ]
        
        for line in lines:
            lower = line.lower()
            
            # Check if line matches a step pattern to avoid treating it as a header
            # (e.g. "Step 1: Preparation" containing "preparation" header keyword)
            is_step_candidate = False
            for pat in step_patterns:
                if re.match(pat, line):
                    is_step_candidate = True
                    break

            # Header detection
            if not is_step_candidate and any(h in lower for h in headers) and len(line) < 30:
                in_section = True
                continue
            
            if in_section:
                # Check if we hit end or notes
                if 'notes' in lower and len(line) < 10:
                    break
                
                # Try matching valid step headers
                matched = None
                for pat in step_patterns:
                    m = re.match(pat, line)
                    if m:
                        matched = m
                        break
                
                if matched:
                    # New step found
                    # Group 2 comes from simple patterns, Group 2 also from Step pattern
                    # Pattern 1: (d) (text) -> 2
                    # Pattern 2: (d) (text) -> 2
                    # Pattern 3: (d) (text) -> 2
                    title = matched.group(2)
                    
                    steps.append(ParsedStep(
                        step_index=len(steps),
                        title=title[:200],
                        bullets=[title] # Treat the line as the first bullet too often handy
                    ))
                else:
                    # Append to previous step if exists
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
