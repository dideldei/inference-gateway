#!/bin/bash
# Health check script for the inference gateway

set -e

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8090}"

echo "Checking gateway health at ${GATEWAY_URL}..."

response=$(curl -s -w "\n%{http_code}" "${GATEWAY_URL}/health" || echo "000")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "✓ Gateway is healthy"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    exit 0
else
    echo "✗ Gateway health check failed (HTTP $http_code)"
    echo "$body"
    exit 1
fi
