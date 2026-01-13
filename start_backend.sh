#!/bin/bash
# Force port 9202 to be used
export APP_PORT=9202
./venv_new/bin/uvicorn main:app --port 9202 --host 0.0.0.0
