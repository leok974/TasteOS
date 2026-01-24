import pytest
from app.parsing import RuleBasedParser

def test_rule_based_parser_simple():
    text = """
    Pancakes
    
    Ingredients:
    1 cup flour
    2 eggs
    1/2 cup milk
    
    Instructions:
    1. Mix everything.
    2. Cook.
    """
    
    parser = RuleBasedParser()
    recipe = parser.parse(text)
    
    assert recipe.title == "Pancakes"
    assert len(recipe.ingredients) == 3
    assert recipe.ingredients[0].name == "flour"
    assert recipe.ingredients[0].qty == 1
    assert recipe.ingredients[0].unit == "cup"
    
    assert len(recipe.steps) == 2
    assert recipe.steps[0].step_index == 0
    assert "Mix everything" in recipe.steps[0].bullets[0]

def test_rule_based_parser_unstructured():
    text = """
    Simple Pasta
    
    What you need:
    - 500g spaghetti
    - Tomato sauce
    - Cheese
    
    Method:
    Boil water.
    Cook pasta.
    Add sauce.
    """
    
    parser = RuleBasedParser()
    recipe = parser.parse(text)
    
    assert recipe.title == "Simple Pasta"
    assert len(recipe.ingredients) == 3
    assert len(recipe.steps) == 1 # Might be 1 step with multiple bullets or 3 steps depending on logic
    # My logic: non-numbered lines might be appended to one step or separate?
    # Logic: "if steps: append, else: create new".
    # Since "Boil water" is first, it creates step 0. 
    # "Cook pasta" appends to step 0.
    assert len(recipe.steps[0].bullets) == 3

def test_rule_based_parser_numbered_unstructured():
    text = """
    Burger
    
    Ingredients
    1 bun
    1 patty
    
    Steps
    1. Grill patty.
    2. Toast bun.
    Assemble.
    """
    parser = RuleBasedParser()
    recipe = parser.parse(text)
    
    assert len(recipe.steps) == 2
    # Check that "Assemble." is in the bullets (exact match with dot from input)
    assert any("Assemble" in b for b in recipe.steps[1].bullets)
