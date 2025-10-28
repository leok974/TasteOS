# TasteOS Variant Generation - Implementation Complete

## Summary

Implemented AI-powered recipe variant generation using **LangGraph** workflow engine and **GPT-4**. This is the core differentiating feature of TasteOS.

## What Was Built

### 1. LangGraph Agent (`tasteos_api/agents/variant_generator.py`)

**VariantGeneratorAgent** - A stateful workflow with 4 stages:

1. **Analyze Recipe** - Understand structure, ingredients, and techniques
2. **Generate Changes** - Create specific modifications based on variant type
3. **Apply Changes** - Transform the original recipe with AI suggestions
4. **Validate Variant** - Check coherence and feasibility, assign confidence score

**Supported Variant Types:**
- `dietary` - Convert to vegetarian, vegan, gluten-free, etc.
- `cuisine` - Adapt recipe to different culinary traditions
- `ingredient_substitution` - Replace specific ingredients
- `simplify` - Reduce complexity and prep time
- `upscale` - Elevate with premium ingredients and techniques

### 2. Complete API Endpoints (`tasteos_api/routers/variants.py`)

✅ **POST /api/v1/variants/generate** - Generate new variant with LangGraph
- Requires: `recipe_id`, `variant_type`
- Optional: `dietary_restriction`, `target_cuisine`, `substitutions`
- Returns: Full variant with changes, metadata, and confidence score

✅ **GET /api/v1/variants/{variant_id}** - Retrieve specific variant

✅ **GET /api/v1/variants/recipe/{recipe_id}** - List all variants for a recipe

✅ **POST /api/v1/variants/{variant_id}/approve** - Approve a generated variant

✅ **GET /api/v1/variants/{variant_id}/diff** - Get structured diff showing all changes

### 3. Test Script (`apps/api/scripts/test_variant.ps1`)

Automated test suite for variant generation:
- Creates dietary variants (vegetarian)
- Creates cuisine variants (Italian → Mexican)
- Retrieves diffs
- Lists all variants
- Approves variants

## How It Works

### Workflow Diagram

```
Original Recipe
      ↓
[Analyze Recipe] ← User preferences (dietary, cuisine, etc.)
      ↓
[Generate Changes] ← AI proposes specific modifications
      ↓
[Apply Changes] ← Transform ingredients/instructions
      ↓
[Validate Variant] ← Check quality & coherence
      ↓
Variant + Confidence Score
```

### Example: Dietary Variant

**Input:**
- Recipe: Spaghetti Carbonara (eggs, bacon, parmesan)
- Variant Type: dietary
- Dietary Restriction: vegetarian

**AI Process:**
1. Identifies non-vegetarian ingredients (bacon, eggs)
2. Suggests alternatives (mushrooms, cashew cream)
3. Adjusts cooking techniques
4. Validates flavor profile

**Output:**
```json
{
  "title": "Vegetarian Carbonara",
  "changes": [
    {
      "type": "ingredient",
      "original": "bacon",
      "new": "smoked mushrooms",
      "reason": "Provides umami without meat"
    },
    {
      "type": "ingredient",
      "original": "eggs",
      "new": "cashew cream",
      "reason": "Creates creamy texture"
    }
  ],
  "confidence_score": 0.85
}
```

## Architecture Highlights

### LangGraph State Management

```python
class VariantState(TypedDict):
    messages: list[BaseMessage]
    recipe_id: UUID
    original_recipe: dict
    variant_type: str
    user_preferences: dict
    generated_variant: dict | None
    changes: list[dict]
    confidence_score: float
```

State flows through each node, accumulating knowledge and transformations.

### Prompt Engineering

Each variant type has a custom prompt template:

**Dietary Variant:**
```
Create a {dietary_type} version of this recipe.
- Replace incompatible ingredients
- Maintain similar flavor profile
- Note texture/taste differences
```

**Cuisine Adaptation:**
```
Adapt to {target_cuisine} cuisine.
- Use authentic ingredients/techniques
- Maintain core concept
- Suggest traditional accompaniments
```

### Change Tracking

Every modification is structured and traceable:

```python
{
  "type": "ingredient",
  "original": "butter",
  "new": "olive oil",
  "reason": "Healthier fat option"
}
```

## Testing

### Prerequisites

1. **OpenAI API Key** must be set in `.env`:
   ```bash
   OPENAI_API_KEY=sk-...
   ```

2. **API must be running**:
   ```bash
   pnpm dev:api
   ```

3. **User logged in** with token:
   ```bash
   .\apps\api\scripts\login.ps1
   ```

### Run Variant Tests

```powershell
.\apps\api\scripts\test_variant.ps1 -Token $env:TASTEOS_TOKEN
```

**Expected Output:**
```
✓ Found recipe: Spaghetti Carbonara (ID: 1b2e92aa...)
✓ SUCCESS - Generated variant:
  Title: Vegetarian Carbonara
  Type: dietary
  Status: generated
  Confidence: 0.85
  Changes: 3 modifications
```

## Database Schema

Variants are stored with full traceability:

```sql
CREATE TABLE recipe_variants (
    id UUID PRIMARY KEY,
    parent_recipe_id UUID REFERENCES recipes(id),
    user_id UUID REFERENCES users(id),
    title VARCHAR,
    description TEXT,
    variant_type VARCHAR,
    status VARCHAR, -- draft, generated, reviewed, approved
    changes JSONB, -- Structured change list
    generation_metadata JSONB, -- AI metadata
    confidence_score FLOAT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Security

✅ **Authorization** - Users can only generate variants of their own recipes
✅ **API Key Protection** - OpenAI key never exposed to frontend
✅ **Rate Limiting** - Ready for usage tracking (for billing)
✅ **Validation** - All inputs sanitized before LLM processing

## Performance Considerations

- **Async Processing** - All LangGraph operations are async
- **Streaming Ready** - Can add streaming responses for long generations
- **Caching** - Can cache similar variant requests
- **Cost Tracking** - Generation metadata includes token counts

## Next Steps

### Immediate Enhancements

1. **Add more variant types**:
   - `scale` - Adjust servings (2 → 8 people)
   - `season` - Adapt to seasonal ingredients
   - `equipment` - Adapt to available kitchen tools
   - `time` - Quick version vs slow-cook version

2. **Streaming responses** - Show generation progress

3. **Variant comparison UI** - Side-by-side diff visualization

4. **User feedback loop** - Let users rate variants to improve prompts

### Advanced Features

1. **Multi-step variants** - Chain transformations (dietary + simplified)

2. **Ingredient substitution engine** - Smart alternatives based on:
   - Allergies
   - Availability
   - Preference
   - Cost

3. **Nutritional analysis** - Calculate nutrition for each variant

4. **Cost estimation** - Compare ingredient costs

5. **LangGraph checkpoints** - Resume interrupted generations

6. **Human-in-the-loop** - Approve changes before finalizing

## Usage Tracking (For Billing)

Each variant generation can be counted for usage limits:

```python
# Free tier: 10 variants/month
# Pro tier: 100 variants/month
# Enterprise: Unlimited

@router.post("/generate")
async def generate_variant(...):
    # Check user's plan and usage
    await check_variant_quota(current_user)
    
    # Generate variant
    result = await variant_agent.generate_variant(...)
    
    # Increment usage counter
    await increment_usage(current_user, "variants_generated")
```

## Cost Analysis

Using GPT-4 for variant generation:

- **Per variant**: ~2,000-4,000 tokens
- **Cost**: $0.03-$0.12 per variant
- **Revenue**: Charge $0.50/variant or bundle in subscription

**Margins:**
- Free tier (10/month): $1.20 cost
- Pro tier ($9.99/month, 100 variants): $12 cost → Need usage-based pricing
- Enterprise: Custom pricing

## Documentation

### For Frontend Developers

```typescript
// Generate a dietary variant
const variant = await fetch('/api/v1/variants/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    recipe_id: recipeId,
    variant_type: 'dietary',
    dietary_restriction: 'vegan'
  })
});

const data = await variant.json();
console.log(`Generated: ${data.title}`);
console.log(`Confidence: ${data.confidence_score}`);
```

### For AI/ML Engineers

The LangGraph agent is extensible:

1. Add new nodes to the workflow
2. Customize prompts for your use case
3. Integrate other LLMs (Claude, Gemini)
4. Add retrieval-augmented generation (RAG) for recipe knowledge

## Success Metrics

Track these KPIs:

- **Generation success rate** - % of variants with confidence > 0.7
- **User approval rate** - % of generated variants marked "approved"
- **Time to generate** - Avg latency for variant creation
- **Token usage** - Total tokens per variant (cost optimization)
- **User engagement** - % of users who generate >1 variant

## Conclusion

🎉 **Variant generation is now fully functional!**

This is TasteOS's core value proposition - AI-powered recipe adaptation. Users can now:

- Convert any recipe to match dietary needs
- Adapt recipes across cuisines
- Substitute ingredients intelligently
- Simplify or elevate dishes
- Get AI confidence scores for each variant

**Next priority**: Build the frontend UI to showcase this feature! 🚀

