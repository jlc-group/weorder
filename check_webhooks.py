
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_webhooks():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n=== Webhook Status Check ===\n")
        
        # 1. Last 5 Webhook Logs
        sql = """
        SELECT platform, event_type, process_result, received_at, process_error
        FROM webhook_log
        ORDER BY received_at DESC
        LIMIT 5
        """
        logs = conn.execute(text(sql)).fetchall()
        
        if not logs:
            print("No webhook logs found in database.")
        else:
            print(f"{'Time':<25} | {'Platform':<10} | {'Event':<25} | {'Status':<10} | {'Error'}")
            print("-" * 100)
            for row in logs:
                created_at = row.received_at.strftime("%Y-%m-%d %H:%M:%S")
                error_msg = row.process_error[:30] + "..." if row.process_error else "-"
                status = str(row.process_result) if row.process_result else "PENDING"
                print(f"{created_at:<25} | {row.platform:<10} | {row.event_type:<25} | {status:<10} | {error_msg}")

if __name__ == "__main__":
    check_webhooks()
