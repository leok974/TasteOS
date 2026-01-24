from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel

class ParsedIngredient(BaseModel):
    name: str
    qty: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None

class ParsedStep(BaseModel):
    step_index: int
    title: str
    bullets: List[str] = []
    minutes_est: Optional[int] = None

class ParsedRecipe(BaseModel):
    title: str
    servings: Optional[int] = None
    time_minutes: Optional[int] = None
    cuisines: List[str] = []
    tags: List[str] = []
    ingredients: List[ParsedIngredient] = []
    steps: List[ParsedStep] = []
    
class RecipeParser(ABC):
    @abstractmethod
    def parse(self, text: str, hints: dict = None) -> ParsedRecipe:
        """Parse raw text into a structured Recipe object."""
        pass
