#!/bin/bash
# WeOrder - Status Script
# Usage: ./status.sh

echo "📊 WeOrder Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Backend
BACKEND_STATUS=$(curl -s http://localhost:9203/health -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
if [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ Backend:  Running (port 9203)"
else
    echo "❌ Backend:  Not running"
fi

# Check Frontend
FRONTEND_STATUS=$(curl -s http://localhost:5173 -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend: Running (port 5173)"
else
    echo "❌ Frontend: Not running"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show processes
echo ""
echo "Running processes:"
ps aux | grep -E "(uvicorn main|vite)" | grep -v grep | awk '{print "  PID " $2 ": " $11 " " $12}'
