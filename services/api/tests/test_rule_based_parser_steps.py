
import pytest
from app.parsing.rule_based_parser import RuleBasedParser

def test_steps_parentheses():
    text = """
    Ingredients:
    Anything
    
    Instructions:
    1) Boil water.
    2) Add pasta.
    3) Eat.
    """
    parser = RuleBasedParser()
    result = parser.parse(text)
    
    assert len(result.steps) == 3
    assert "Boil water" in result.steps[0].title
    assert "Add pasta" in result.steps[1].title
    assert "Eat" in result.steps[2].title

def test_steps_step_prefix():
    text = """
    Method:
    Step 1: Preparation.
    Step 2: Cooking.
    """
    parser = RuleBasedParser()
    result = parser.parse(text)
    
    assert len(result.steps) == 2
    assert "Preparation" in result.steps[0].title
    assert "Cooking" in result.steps[1].title

def test_steps_bullets_inside():
    text = """
    Instructions:
    1. Prepare sauce.
    - Chop onions
    - Chop garlic
    2. Cook pasta.
    """
    parser = RuleBasedParser()
    result = parser.parse(text)
    
    assert len(result.steps) == 2
    assert "Prepare sauce" in result.steps[0].title
    # The bullets logic in parser might put "- Chop onions" as a bullet for step 1
    # Check bullets
    assert len(result.steps[0].bullets) >= 2 # title is often in bullets too in current impl
    assert any("onions" in b for b in result.steps[0].bullets)

def test_steps_mixed_formats_and_emojis():
    # If we implement emoji normalization
    text = """
    Instructions:
    1️⃣ First step
    2) Second step
    3. Third step
    """
    parser = RuleBasedParser()
    result = parser.parse(text)
    
    assert len(result.steps) == 3
    assert "First step" in result.steps[0].title
    assert "Second step" in result.steps[1].title
    
