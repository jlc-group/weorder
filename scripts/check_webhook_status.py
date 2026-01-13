
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.integration import WebhookLog

def check_webhooks():
    session = SessionLocal()
    try:
        # Check last 7 days
        since = datetime.now() - timedelta(days=7)
        
        # Count total webhooks
        total = session.query(WebhookLog).filter(
            WebhookLog.received_at >= since
        ).count()
        
        print(f"=== Webhook Log Summary (Last 7 Days) ===")
        print(f"Total Webhooks Received: {total}")
        
        if total == 0:
            print("\n⚠️ No webhooks received recently!")
            print("   This could mean:")
            print("   1. Backend is not running (Uvicorn)")
            print("   2. Cloudflare Tunnel is not active")
            print("   3. Platforms haven't sent any webhooks yet")
            return
        
        # Recent 5 logs
        recent = session.query(WebhookLog).order_by(
            WebhookLog.received_at.desc()
        ).limit(5).all()
        
        print("\n--- Recent Webhooks ---")
        for log in recent:
            status = "✅" if log.process_result == "UPDATED" else ("⏳" if not log.processed else "❌")
            print(f"{status} [{log.platform}] {log.event_type} @ {log.received_at} -> {log.process_result or 'PENDING'}")

    finally:
        session.close()

if __name__ == "__main__":
    check_webhooks()
