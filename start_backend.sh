#!/bin/bash
# Force port 9203 to be used
export APP_PORT=9203
./.venv/bin/uvicorn main:app --port 9203 --host 0.0.0.0
