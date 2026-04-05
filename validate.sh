#!/bin/bash
REPO_DIR="."
PING_URL="http://127.0.0.1:7860"
CURL_OUTPUT="curl_output.txt"
DOCKER_BUILD_TIMEOUT=300

BOLD="\033[1m"
GREEN="\033[32m"
NC="\033[0m"

log() { echo -e "$1"; }
pass() { log "${GREEN}✓ $1${NC}"; }
fail() { log "✗ $1"; }
hint() { log "  Hint: $1"; }
stop_at() { echo "Failed at $1"; exit 1; }
run_with_timeout() { timeout "$1" "${@:2}"; }

log "${BOLD}Step 1/3: Checking /reset endpoint${NC} ..."
HTTP_CODE=$(curl -s -o "$CURL_OUTPUT" -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$PING_URL/reset" --max-time 30 2>/dev/null || printf "000")

if [ "$HTTP_CODE" = "200" ]; then
  pass "HF Space is live and responds to /reset"
else
  fail "HF Space /reset returned HTTP $HTTP_CODE (expected 200)"
  stop_at "Step 1"
fi

log "${BOLD}Step 2/3: Running docker build${NC} ..."
DOCKER_CONTEXT="$REPO_DIR"
BUILD_OK=false
BUILD_OUTPUT=$(docker build "$DOCKER_CONTEXT" 2>&1) && BUILD_OK=true

if [ "$BUILD_OK" = true ]; then
  pass "Docker build succeeded"
else
  fail "Docker build failed"
  printf "%s\n" "$BUILD_OUTPUT" | tail -20
  stop_at "Step 2"
fi

log "${BOLD}Step 3/3: Running openenv validate${NC} ..."
openenv validate
if [ $? -eq 0 ]; then
  pass "openenv validate passed"
else
  fail "openenv validate failed"
  stop_at "Step 3"
fi
