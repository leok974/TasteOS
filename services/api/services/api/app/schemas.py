
# --- Unit Conversion ---

class UnitConvertRequest(BaseModel):
    qty: float
    from_unit: str
    to_unit: str
    ingredient_name: Optional[str] = None
    force_cross_type: bool = False

class UnitConvertResponse(BaseModel):
    qty: float
    unit: str
    confidence: Literal["high", "medium", "low", "none"]
    note: Optional[str] = None
    is_approx: bool = False
