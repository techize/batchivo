#!/bin/bash
#
# Integration Test Script for Nozzly API
# Tests the complete authentication and spool creation flow
#
# Usage: ./integration_test.sh [API_BASE_URL]
# Example: ./integration_test.sh https://nozzly.app/api/v1
#

set -e

# Configuration
API_BASE_URL="${1:-https://nozzly.app/api/v1}"
TEST_EMAIL="test@example.com"
TEST_PASSWORD="testpassword123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_test() {
    echo -e "\n${YELLOW}[TEST]${NC} $1"
    TESTS_RUN=$((TESTS_RUN + 1))
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Cleanup function
cleanup() {
    if [ -f "/tmp/nozzly_test_response.json" ]; then
        rm -f /tmp/nozzly_test_response.json
    fi
}

trap cleanup EXIT

# ============================================================================
# Test 1: Health Check
# ============================================================================
log_test "Health check endpoint"
if curl -s -f "${API_BASE_URL}/health" > /tmp/nozzly_test_response.json 2>&1; then
    log_pass "Health check passed"
else
    log_fail "Health check failed"
    cat /tmp/nozzly_test_response.json
fi

# ============================================================================
# Test 2: Login
# ============================================================================
log_test "User login"
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    ACCESS_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
    REFRESH_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.refresh_token')

    if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
        log_pass "Login successful - received access token"
    else
        log_fail "Login response missing access_token"
        echo "$RESPONSE_BODY" | jq .
    fi
else
    log_fail "Login failed with HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY" | jq .
    exit 1
fi

# ============================================================================
# Test 3: Get User Info (/users/me)
# ============================================================================
log_test "Get user info (/users/me)"
USER_RESPONSE=$(curl -s -X GET "${API_BASE_URL}/users/me" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$USER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    USER_EMAIL=$(echo "$RESPONSE_BODY" | jq -r '.email')
    TENANT_ID=$(echo "$RESPONSE_BODY" | jq -r '.tenant_id')

    if [ "$USER_EMAIL" = "$TEST_EMAIL" ]; then
        log_pass "Retrieved user info successfully"
        log_info "User: $USER_EMAIL, Tenant: $TENANT_ID"
    else
        log_fail "User email mismatch"
        echo "$RESPONSE_BODY" | jq .
    fi
else
    log_fail "Get user info failed with HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY" | jq .
fi

# ============================================================================
# Test 4: List Material Types
# ============================================================================
log_test "List material types (/spools/material-types)"
MATERIALS_RESPONSE=$(curl -s -X GET "${API_BASE_URL}/spools/material-types" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$MATERIALS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$MATERIALS_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    MATERIAL_COUNT=$(echo "$RESPONSE_BODY" | jq 'length')

    if [ "$MATERIAL_COUNT" -ge 8 ]; then
        log_pass "Retrieved $MATERIAL_COUNT material types"

        # Extract PLA material ID for next test
        PLA_ID=$(echo "$RESPONSE_BODY" | jq -r '.[] | select(.code == "PLA") | .id')
        log_info "PLA material ID: $PLA_ID"
    else
        log_fail "Expected at least 8 material types, got $MATERIAL_COUNT"
        echo "$RESPONSE_BODY" | jq .
    fi
else
    log_fail "List material types failed with HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY" | jq .
fi

# ============================================================================
# Test 5: List Spools (should work with same token)
# ============================================================================
log_test "List spools (/spools)"
SPOOLS_RESPONSE=$(curl -s -X GET "${API_BASE_URL}/spools" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$SPOOLS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SPOOLS_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    SPOOL_COUNT=$(echo "$RESPONSE_BODY" | jq '.total')
    log_pass "Retrieved spools list (total: $SPOOL_COUNT)"
else
    log_fail "List spools failed with HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY" | jq .
fi

# ============================================================================
# Test 6: Create Spool
# ============================================================================
if [ -n "$PLA_ID" ] && [ "$PLA_ID" != "null" ]; then
    log_test "Create new spool"

    RANDOM_ID=$((RANDOM % 10000))
    SPOOL_DATA=$(cat <<EOF
{
    "spool_id": "TEST-${RANDOM_ID}",
    "brand": "Test Brand",
    "material_type_id": "${PLA_ID}",
    "color": "Red",
    "finish": "matte",
    "diameter_mm": 1.75,
    "initial_weight_g": 1000.0,
    "current_weight_g": 1000.0
}
EOF
)

    CREATE_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/spools" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$SPOOL_DATA" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "201" ]; then
        CREATED_SPOOL_ID=$(echo "$RESPONSE_BODY" | jq -r '.id')
        CREATED_MATERIAL_CODE=$(echo "$RESPONSE_BODY" | jq -r '.material_type_code')

        if [ "$CREATED_MATERIAL_CODE" = "PLA" ]; then
            log_pass "Created spool TEST-${RANDOM_ID} with material PLA"
            log_info "Spool ID: $CREATED_SPOOL_ID"
        else
            log_fail "Created spool but material type is wrong: $CREATED_MATERIAL_CODE"
            echo "$RESPONSE_BODY" | jq .
        fi
    else
        log_fail "Create spool failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY" | jq .
    fi
else
    log_fail "Skipping spool creation - no PLA material ID"
fi

# ============================================================================
# Test 7: Verify Authentication Consistency
# ============================================================================
log_test "Verify authentication consistency (multiple sequential requests)"

CONSISTENCY_PASS=true

for i in {1..5}; do
    log_info "Request $i/5"

    # Alternate between /users/me and /spools/material-types
    if [ $((i % 2)) -eq 0 ]; then
        ENDPOINT="/users/me"
    else
        ENDPOINT="/spools/material-types"
    fi

    RESPONSE=$(curl -s -X GET "${API_BASE_URL}${ENDPOINT}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" != "200" ]; then
        log_fail "Request $i to $ENDPOINT failed with HTTP $HTTP_CODE"
        CONSISTENCY_PASS=false
        break
    fi
done

if [ "$CONSISTENCY_PASS" = true ]; then
    log_pass "All 5 sequential requests succeeded"
fi

# ============================================================================
# Test Summary
# ============================================================================
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo "Tests Run:    $TESTS_RUN"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "========================================"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
