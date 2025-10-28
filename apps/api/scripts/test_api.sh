#!/usr/bin/env bash
set -e

TOKEN="${1:-}"
API_BASE="${2:-http://127.0.0.1:8000}"

if [ -z "$TOKEN" ]; then
    echo "ERROR: Token is required. Usage: ./test_api.sh <token> [api_base]"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"
CONTENT_TYPE="Content-Type: application/json"

log() {
  echo ""
  echo "==================================="
  echo "=== $1"
  echo "==================================="
}

echo ""
echo "========================================"
echo "TasteOS API Smoke Test"
echo "API Base: $API_BASE"
echo "Token: [REDACTED - length ${#TOKEN}]"
echo "========================================"

# 1. Test /auth/me
log "TEST 1: GET /auth/me"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "$AUTH_HEADER" \
  "$API_BASE/api/v1/auth/me" | jq . || echo "FAILED"

# 2. Test GET /recipes
log "TEST 2: GET /recipes"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "$AUTH_HEADER" \
  "$API_BASE/api/v1/recipes/" | jq . || echo "FAILED"

# 3. Test POST /recipes
log "TEST 3: POST /recipes"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -X POST \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "title":"Spaghetti Carbonara",
    "description":"Classic Italian pasta dish",
    "servings":4,
    "prep_time":10,
    "cook_time":20,
    "difficulty":"medium",
    "cuisine":"italian",
    "tags":["pasta","italian","dinner"],
    "ingredients":[
      {"item":"spaghetti","amount":"400g","notes":""},
      {"item":"eggs","amount":"4","notes":""},
      {"item":"parmesan","amount":"100g","notes":"grated"}
    ],
    "instructions":[
      {"step":1,"text":"Boil pasta in salted water"},
      {"step":2,"text":"Mix eggs and cheese in a bowl"},
      {"step":3,"text":"Drain pasta and mix with egg mixture"}
    ]
  }' \
  "$API_BASE/api/v1/recipes/" | jq . || echo "FAILED"

echo ""
echo "========================================"
echo "Smoke test complete"
echo "========================================"
echo ""
