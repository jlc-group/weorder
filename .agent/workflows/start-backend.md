---
description: How to correctly start the WeOrder backend server
---

# Start WeOrder Backend

Always follow these steps to start the backend server. **DO NOT GUESS THE PORT.**

1. **Verify Port Configuration**: 
   - Check `app/core/config.py` or `.env`. The default project port is **9203**.
   - **NEVER** use port 8000 unless explicitly instructed to override the configuration.

2. **Run Server**:
   Run the following command from the project root:

   ```bash
   venv/bin/uvicorn main:app --reload --port 9203
   ```

   *Note: If port 9203 is busy, find and kill the process using it, do not change the port.*
