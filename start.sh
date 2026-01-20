#!/bin/bash
# WeOrder - Start Script
# Usage: ./start.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Starting WeOrder..."

# Stop any existing processes first
./stop.sh 2>/dev/null

sleep 2

# Start Backend
echo "📦 Starting Backend (port 9203)..."
nohup .venv/bin/uvicorn main:app --port 9203 > /tmp/weorder-backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/weorder-backend.pid
echo "   Backend PID: $BACKEND_PID"

# Start Frontend
echo "🎨 Starting Frontend (port 5173)..."
cd frontend
nohup npm run dev > /tmp/weorder-frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/weorder-frontend.pid
echo "   Frontend PID: $FRONTEND_PID"

cd "$PROJECT_DIR"

# Start Auto Sync Scheduler
echo "🔄 Starting Auto Sync Scheduler..."
nohup .venv/bin/python3 scheduler.py > /tmp/weorder-scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo $SCHEDULER_PID > /tmp/weorder-scheduler.pid
echo "   Scheduler PID: $SCHEDULER_PID"

# Wait for services to start
echo ""
echo "⏳ Waiting for services..."
sleep 8

# Check status
BACKEND_STATUS=$(curl -s http://localhost:9203/health -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
FRONTEND_STATUS=$(curl -s http://localhost:5173 -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ Backend:  http://localhost:9203"
else
    echo "⏳ Backend:  Starting... (check /tmp/weorder-backend.log)"
fi

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend: http://localhost:5173"
else
    echo "⏳ Frontend: Starting... (check /tmp/weorder-frontend.log)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Login: Chack / 1234"
echo "📝 Logs:  tail -f /tmp/weorder-backend.log"
echo "🛑 Stop:  ./stop.sh"
