#!/bin/bash
cd "$(dirname "$0")"

echo "Starting embodied-robot-brain backend on port 8013..."
nohup python -m uvicorn backend.app:app --host 0.0.0.0 --port 8013 > app.log 2>&1 &
PID=$!
echo "embodied-robot-brain started with PID: $PID"
echo "Backend: http://localhost:8013"
