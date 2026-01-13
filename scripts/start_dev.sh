#!/bin/bash

# Configuration
BACKEND_PORT=9202
FRONTEND_PORT=5173

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== WeOrder Startup Script ===${NC}"

# 1. Check/Kill existing processes
echo -e "\nChecking for existing processes..."
PID_BACKEND=$(lsof -t -i:$BACKEND_PORT)
if [ ! -z "$PID_BACKEND" ]; then
    echo -e "${RED}Killing existing backend on port $BACKEND_PORT (PID: $PID_BACKEND)${NC}"
    kill -9 $PID_BACKEND
fi

PID_FRONTEND=$(lsof -t -i:$FRONTEND_PORT)
if [ ! -z "$PID_FRONTEND" ]; then
    echo -e "${RED}Killing existing frontend on port $FRONTEND_PORT (PID: $PID_FRONTEND)${NC}"
    kill -9 $PID_FRONTEND
fi

# 2. Start Backend
echo -e "\n${GREEN}Starting Backend on Port $BACKEND_PORT...${NC}"
# Use standard venv path
if [ -d "venv" ]; then
    PYTHON_CMD="venv/bin/uvicorn"
else
    PYTHON_CMD="uvicorn"
fi

$PYTHON_CMD main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# 3. Start Frontend
echo -e "\n${GREEN}Starting Frontend...${NC}"
cd frontend
npm run dev

# Cleanup on exit
# trap "kill $BACKEND_PID" EXIT
