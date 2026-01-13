#!/usr/bin/env python3
"""
Fetch Sync Job Error Details.
"""
import sys
import os
from sqlalchemy import desc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import SessionLocal
from app.models.integration import SyncJob

db = SessionLocal()

print("=== Checking Latest Sync Job Errors ===")
job = db.query(SyncJob).filter(
    SyncJob.status == 'FAILED'
).order_by(desc(SyncJob.started_at)).first()

if job:
    print(f"Job ID: {job.id}")
    print(f"Platform: {job.platform_config_id}") # Need join for name, but ID is ok
    print(f"Started: {job.started_at}")
    print(f"Error Message: {job.error_message}")
    print(f"Error Details: {job.error_details}")
else:
    print("No failed jobs found in recent history.")

db.close()
