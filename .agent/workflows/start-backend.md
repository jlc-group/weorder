---
description: How to correctly start the WeOrder backend server
---

# Start WeOrder Backend

Always follow these steps to start the backend server. **DO NOT GUESS THE PORT.**

## วิธีที่ 1: Auto-Restart (แนะนำ)

ใช้ batch file ที่จะ auto-restart ถ้า backend crash:

```bash
# Windows - Double-click หรือรัน:
start_backend.bat
```

## วิธีที่ 2: Manual

1. **Verify Port Configuration**: 
   - Check `app/core/config.py` or `.env`. The default project port is **9203**.
   - **NEVER** use port 8000 unless explicitly instructed to override the configuration.

2. **Run Server**:
   ```powershell
   $env:APP_PORT="9203"; .\.venv\Scripts\python.exe -m uvicorn main:app --port 9203 --host 0.0.0.0
   ```

   *Note: If port 9203 is busy, find and kill the process using it, do not change the port.*

3. **ถ้า Port ถูกใช้อยู่**:
   ```powershell
   netstat -ano | findstr ":9203"
   taskkill /PID <pid> /F
   ```

