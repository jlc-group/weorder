---
description: Debug when frontend loads slowly or spins indefinitely
---

# Debug Slow Loading / Infinite Spinner

When the frontend shows an infinite loading spinner or takes forever to load, follow these steps:

## Step 1: Check for Competing Python Processes

```bash
ps aux | grep -E "(python|uvicorn)" | grep -v grep | grep -v "Antigravity"
```

Look for:
- **Backfill scripts** (`backfill_*.py`, `sync_*.py`)
- **AI Data Analyst** (uvicorn on port 8000)
- **Multiprocessing workers** (`from multiprocessing.spawn`)
- **Any other Python scripts** that might be using the database

## Step 2: Check Database Connections

PostgreSQL has limited connection pool. If many processes are holding connections:
- New queries must wait
- Causes API timeouts
- Frontend shows infinite spinner

## Step 3: Stop Competing Processes

Kill any unnecessary Python processes:

```bash
# List all Python processes
ps aux | grep python | grep -v grep

# Kill specific process by PID
kill <PID>
```

## Step 4: Verify Backend is Responsive

```bash
# Health check
curl -s http://localhost:9202/health

# Test dashboard API (should return in <5 seconds)
curl -s -m 10 "http://localhost:9202/api/dashboard/stats?start_date=2026-01-01&end_date=2026-01-17" | head -c 200
```

## Root Cause Summary

| Symptom | Cause |
|---------|-------|
| Infinite spinner | DB connection pool exhausted |
| Backend no error | SQLAlchemy waiting for connections silently |
| Slow API | Other scripts hogging connections |

## Prevention

1. **Don't run heavy scripts** while using the app
2. **Use `--reload` sparingly** - it causes constant restarts
3. **Monitor active processes** before debugging frontend issues
