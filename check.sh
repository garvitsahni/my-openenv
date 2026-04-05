#!/bin/bash

# Pre-deployment Checklist Script for WorkBench HF Space

echo "Running Pre-Deployment Checklist for WorkBench..."
echo "--------------------------------------------------"

# 1. Check Docker Build
echo "[1/4] Building Docker image locally..."
if docker build -t workbench:latest .; then
    echo "PASS: Docker build successful"
else
    echo "FAIL: Docker build failed"
    exit 1
fi

# 2. Start container temporarily
echo "[2/4] Starting Docker container locally..."
container_id=$(docker run -d -p 7860:7860 workbench:latest)
sleep 5 # wait for uvicorn to start

# 3. Check GET /health
echo "[3/4] Requesting GET /health..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7860/health)
if [ "$status_code" -eq 200 ]; then
    echo "PASS: health check passed"
else
    echo "FAIL: health check returned status code $status_code"
    docker stop $container_id > /dev/null
    exit 1
fi

# 4. Check POST /reset
echo "[4/4] Requesting POST /reset..."
reset_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"task_id":"email-triage-easy","seed":42}' http://localhost:7860/reset)
if [ "$reset_code" -eq 200 ]; then
    echo "PASS: task reset successful"
else
    echo "FAIL: task reset returned status code $reset_code"
    docker stop $container_id > /dev/null
    exit 1
fi

# Cleanup
echo "Cleaning up local container..."
docker stop $container_id > /dev/null
echo "--------------------------------------------------"
echo "ALL PRE-FLIGHT CHECKS PASSED. Ready for Deployment!"
