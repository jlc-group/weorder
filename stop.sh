#!/bin/bash
# WeOrder - Stop Script
# Usage: ./stop.sh

echo "🛑 Stopping WeOrder..."

# Kill by PID files
if [ -f /tmp/weorder-backend.pid ]; then
    kill $(cat /tmp/weorder-backend.pid) 2>/dev/null
    rm /tmp/weorder-backend.pid
fi

if [ -f /tmp/weorder-frontend.pid ]; then
    kill $(cat /tmp/weorder-frontend.pid) 2>/dev/null
    rm /tmp/weorder-frontend.pid
fi

if [ -f /tmp/weorder-scheduler.pid ]; then
    kill $(cat /tmp/weorder-scheduler.pid) 2>/dev/null
    rm /tmp/weorder-scheduler.pid
fi

# Kill any remaining processes (force kill with -9)
pkill -9 -f "uvicorn main:app" 2>/dev/null
pkill -9 -f "vite" 2>/dev/null
pkill -9 -f "scheduler.py" 2>/dev/null
pkill -9 -f "node.*weorder/frontend" 2>/dev/null

# Kill processes by port if still running
lsof -ti:9203 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null

sleep 1

echo "✅ All services stopped"
