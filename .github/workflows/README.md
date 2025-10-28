# CI/CD Setup

This document explains the Continuous Integration setup for TasteOS.

## GitHub Actions

### Test Suite Workflow

**File:** `.github/workflows/test.yml`

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

**Jobs:**

#### 1. Backend Tests (`test-api`)

Runs the Phase 3 async test suite against the FastAPI backend:

- Python 3.11
- pytest with async support (pytest-asyncio, httpx)
- In-memory SQLite database (`sqlite+aiosqlite:///:memory:`)
- Mocked agent functions (no LLM API calls)

**Current Status:** ✅ 10 tests passing

```bash
# Local equivalent:
cd apps/api
pytest tasteos_api/tests -q
```

#### 2. Frontend Tests (`test-app`)

**Status:** Coming soon

Planned to run Vitest tests for React components:
- PantryTable smoke tests
- PlannerView rendering tests
- ShoppingList interaction tests

## Required Secrets

Configure these in GitHub repository settings → Secrets and variables → Actions:

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for agent tests | Optional - agents are mocked in tests |

**Note:** The test suite doesn't actually call OpenAI APIs (agents are mocked), so this secret is optional. It's included for future integration tests.

## Local Testing Before Push

Always run tests locally before pushing:

```bash
# Backend
cd apps/api
pytest tasteos_api/tests -q

# Expected: 10 passed, warnings in ~0.5s
```

## Coverage Reports

The workflow generates coverage reports but doesn't enforce minimums yet.

To see coverage locally:

```bash
cd apps/api
pytest tasteos_api/tests --cov=tasteos_api --cov-report=html
# Open htmlcov/index.html in browser
```

**Current Coverage:**
- Overall: 49%
- Test files: 95-100%
- Routers: 43-49%

## Adding New Tests

When adding new features:

1. **Write tests first** (TDD approach recommended)
2. **Add to appropriate test file:**
   - `test_pantry.py` - Pantry CRUD operations
   - `test_planner.py` - Meal planning features
   - `test_shopping.py` - Shopping list features
3. **Mock agent functions** to avoid LLM API calls
4. **Use async patterns** (`@pytest.mark.asyncio`, `await`)
5. **Run locally** before committing

Example test structure:

```python
@pytest.mark.asyncio
async def test_new_feature(async_client, test_user):
    with patch("tasteos_api.agents.some_agent.function") as mock_fn:
        mock_fn.return_value = {"expected": "data"}
        
        resp = await async_client.post("/api/v1/endpoint", json={...})
        
        assert resp.status_code == 200
        assert resp.json()["field"] == "value"
```

## Troubleshooting CI Failures

### Tests pass locally but fail in CI

1. **Check environment variables:** CI may have different `.env` values
2. **Database differences:** Local may use PostgreSQL, CI uses SQLite
3. **Timing issues:** Add `pytest-timeout` for flaky async tests

### Import errors

1. **Missing dependencies:** Update `requirements.txt`
2. **Path issues:** CI runs from repo root, not `apps/api/`

### Coverage drops unexpectedly

1. **New code without tests:** Add tests for new features
2. **Dead code:** Remove unused imports/functions

## Future Enhancements

- [ ] Enforce minimum coverage threshold (e.g., 60%)
- [ ] Add frontend tests with Vitest
- [ ] E2E tests with Playwright
- [ ] Deploy preview environments on PR
- [ ] Automated dependency updates (Dependabot)
- [ ] Performance benchmarking
- [ ] Security scanning (Snyk, GitHub Security)

## Resources

- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [httpx testing docs](https://www.python-httpx.org/advanced/#calling-into-python-web-apps)
- [GitHub Actions Python guide](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)

---

**This is where TasteOS stops being "my local project" and starts being "a project I could onboard help to."**
