# TasteOS · Phase 4 Completion Report

**Status date**: October 28, 2025  
**Phase**: 4 — Family Mode (Households + Cultural Memory)

## Highlights

- TasteOS now supports shared households instead of just single-user mode.
- Pantry, Planner, and Shopping are all scoped per-household.
- We now store "how our family actually cooks it" as structured memory.

## Core Features Shipped

### 1. Household Model
- `households` and `household_memberships` tables
- Users can belong to shared spaces
- Multi-user household support with role-based membership (owner/member)

### 2. Pantry Sharing
- Pantry items include `household_id` and `added_by_user_id`
- All reads/writes go through `get_current_household` dependency
- Items are shared across all household members
- Tracking who added each item for attribution

### 3. Household Meal Planning
- `MealPlan` now has `household_id` field
- Supports `notes_per_user` (JSON) so we can track per-person dietary tweaks
- `/planner/today` and `/planner/generate` are household-aware
- Plans are shared but can contain individual preferences

### 4. Shared Grocery List
- `GroceryItem` now has `household_id` and optional `assigned_to_user`
- `/shopping`, `/shopping/generate`, `/shopping/{id}/toggle` are household-aware
- Toggle enforces access control (404 if not in your household)
- Items can be assigned to specific household members

### 5. Cultural Memory
- New model: `recipe_memory`
- New router: `/api/v1/memory` with 4 endpoints:
  - `GET /api/v1/memory/` - List all household recipe memories
  - `POST /api/v1/memory/` - Create new recipe memory
  - `GET /api/v1/memory/{id}` - Get specific memory by ID
  - `DELETE /api/v1/memory/{id}` - Delete recipe memory
- Stores `dish_name`, `origin_notes`, `substitutions` (JSON), `spice_prefs` (JSON), `last_cooked_at`
- This is the "family cookbook" and taste profile
- Tracks who created each memory with `created_by_user`

### 6. Access Dependency
- `get_current_household` dependency added to `core/dependencies.py`
- All protected routes require both `current_user` and `current_household`
- Resolves first household user belongs to (ordered by join date)
- Returns lightweight `SimpleNamespace(id, name)` for performance
- Raises 403 if user not in any household

## Testing & CI

### Test Coverage
- **Phase 3 tests** (single-user async infra): 10/10 passing ✅
- **Phase 4 tests** (household + memory): 8/8 passing ✅
- **Combined core coverage**: 18/18 passing ✅

### Phase 4 Test Breakdown
1. **Memory Tests** (4 tests):
   - `test_create_and_list_memory` - Create and retrieve recipe memories
   - `test_get_memory_by_id` - Fetch specific memory
   - `test_delete_memory` - Delete recipe memory
   - `test_memory_household_isolation` - Verify cross-household boundaries

2. **Isolation Tests** (4 tests):
   - `test_pantry_household_isolation` - Pantry items isolated per household
   - `test_planner_household_isolation` - Meal plans isolated per household
   - `test_shopping_household_isolation` - Grocery lists isolated per household
   - `test_multi_user_household_sharing` - Verify multi-user sharing works

### CI Configuration
- CI now runs `pytest -m "phase3 or phase4"` 
- Future changes cannot silently break shared-household flows
- Both single-user and multi-user scenarios are defended
- Coverage reports include all core functionality

## Migrations & Persistence

### Alembic Setup
- Alembic initialized and configured for SQLModel
- `alembic.ini` configured to use `DATABASE_URL` from `.env`
- `alembic/env.py` imports all models for autogeneration

### Phase 4 Migration
- Migration generated: `9cfae00d59c4_phase_4_add_households_and_recipe_memory.py`
- Creates new tables:
  - `households` - Household entities
  - `household_memberships` - User-household relationships
  - `recipe_memory` - Cultural recipe knowledge
- Adds columns to existing tables:
  - `pantry_items`: `household_id`, `added_by_user_id`
  - `meal_plans`: `household_id`, `notes_per_user`
  - `grocery_items`: `household_id`, `assigned_to_user`
  - `users`: `subscription_status`, `stripe_customer_id` (Phase 2 carryover)

### Deployment Flow
- **Recommended**: Run `alembic upgrade head` instead of `SQLModel.metadata.create_all()`
- Database schema is now versioned and tracked
- Migration history enables safe rollbacks
- Test database uses in-memory SQLite with full schema

## Architecture Patterns

### Household Scoping Pattern
All Phase 4 endpoints follow this pattern:

```python
@router.get("/")
async def list_items(
    current_household: Annotated[object, Depends(get_current_household)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    # Filter by household
    result = await session.exec(
        select(Model).where(Model.household_id == current_household.id)
    )
    return result.all()
```

### Create Pattern
```python
@router.post("/")
async def create_item(
    item_data: ItemCreate,
    current_household: Annotated[object, Depends(get_current_household)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    # Set household and user context
    item = Model(
        **item_data.model_dump(),
        household_id=current_household.id,
        created_by_user=current_user.id
    )
    session.add(item)
    await session.commit()
    return item
```

### Access Control Pattern
```python
# Verify item belongs to current household
if item.household_id != current_household.id:
    raise HTTPException(status_code=404, detail="Not found")
```

## Schema Design

### Model Changes

**New Models:**
- `Household` - Core household entity
- `HouseholdMembership` - Many-to-many user-household relationship
- `RecipeMemory` - Cultural recipe knowledge storage

**Updated Models:**
- `PantryItem` - Added household scoping and user attribution
- `MealPlan` - Added household scoping and per-user notes
- `GroceryItem` - Added household scoping and task assignment

### Schema Pattern (Fixed in Phase 4)
- **Base schemas**: Include all database fields
- **Create schemas**: Only include client-provided fields
- **Router responsibility**: Set `household_id` and `created_by_user` from dependencies
- This prevents 422 validation errors from clients providing system-managed fields

## Exit Criteria ✅

- ✅ Shared pantry works per household
- ✅ Planner can generate a plan for a household and honor per-user notes
- ✅ Shopping list can be shared and toggled safely
- ✅ Family recipes / cultural tweaks are captured and queryable
- ✅ Async tests for both single-user and household scenarios are green
- ✅ Migrations are versioned and tracked
- ✅ CI defends against regressions in household logic
- ✅ All 18 core tests passing with zero failures
- ✅ Consistent patterns established across all routers

## Known Limitations

1. **Single Household Per User**: Current implementation resolves to first household user belongs to
   - Future: Add household switcher UI
   - Future: Support for multiple active household contexts

2. **No Household Invitations**: Users must be manually added to households
   - Future: Invitation flow with email/code
   - Future: Pending membership approval workflow

3. **No Household Admin Features**: All members have equal access
   - Future: Differentiate owner vs member permissions
   - Future: Transfer ownership, remove members

4. **Memory Search**: Recipe memories are listed but not searchable
   - Future: Full-text search on dish names and notes
   - Future: Filter by tags, date ranges, creator

## Migration from Phase 3 to Phase 4

### For Existing Deployments

If you have an existing Phase 3 deployment:

1. **Backup current database**:
   ```bash
   cp tasteos.db tasteos.db.backup
   ```

2. **Run migration**:
   ```bash
   python -m alembic upgrade head
   ```

3. **Create default household for existing users**:
   ```python
   # Run this script or create manually in DB
   from tasteos_api.models import Household, HouseholdMembership
   # Create household for each user
   # Add membership records
   ```

### For New Deployments

1. **Set DATABASE_URL** in `.env`
2. **Run migrations**: `python -m alembic upgrade head`
3. **Start API**: All tables will be created via migration

### For Development

Tests continue to work as-is:
- Test fixtures create household context automatically
- In-memory database spins up with full schema
- No migration needed for test runs

## Tag

**Release tag**: `v0.4.0`  
**Baseline for**: Phase 5  
**Git tag command**:
```bash
git add .
git commit -m "feat(phase4): household sharing and cultural memory"
git tag v0.4.0
git push origin main --tags
```

## Next Steps (Phase 5 Candidates)

1. **Household Management UI**
   - Create/join households
   - Invite members
   - Switch between households

2. **Advanced Recipe Memory**
   - Photo attachments for dishes
   - Rating/favorites system
   - Ingredient preference learning

3. **Collaborative Planning**
   - Real-time updates when household members change plans
   - Comments/discussion on meal plans
   - Vote on meal options

4. **Smart Shopping**
   - Integration with grocery store APIs
   - Price tracking and suggestions
   - Recurring item patterns

5. **Pantry Intelligence**
   - Expiration notifications
   - Recipe suggestions based on current pantry
   - Automatic restock suggestions

---

**Phase 4 Status**: ✅ **COMPLETE**  
**All tests passing**: 18/18 ✅  
**CI protecting**: Phase 3 + Phase 4 ✅  
**Production ready**: Migration path defined ✅
