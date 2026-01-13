
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_sync_status():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n=== Sync Job History (Last 10) ===\n")
        
        sql = """
        SELECT 
            pc.platform,
            sj.job_type,
            sj.status,
            sj.started_at,
            sj.finished_at,
            sj.orders_fetched,
            sj.error_message
        FROM sync_job sj
        JOIN platform_config pc ON sj.platform_config_id = pc.id
        ORDER BY sj.started_at DESC
        LIMIT 10
        """
        jobs = conn.execute(text(sql)).fetchall()
        
        if not jobs:
            print("No sync jobs found.")
        else:
            print(f"{'Started At':<20} | {'Platform':<10} | {'Type':<8} | {'Status':<10} | {'Fetched'} | {'Error'}")
            print("-" * 100)
            for row in jobs:
                started = row.started_at.strftime("%Y-%m-%d %H:%M") if row.started_at else "-"
                err = row.error_message[:20] + "..." if row.error_message else "-"
                print(f"{started:<20} | {row.platform:<10} | {row.job_type:<8} | {row.status:<10} | {row.orders_fetched:<7} | {err}")

if __name__ == "__main__":
    check_sync_status()
