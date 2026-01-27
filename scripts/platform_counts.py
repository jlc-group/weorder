import asyncio
from app.database import get_db
from sqlalchemy import text

async def main():
    async for db in get_db():
        # Get order counts by platform and status
        result = await db.execute(text('''
            SELECT platform, internal_status, COUNT(*) as count 
            FROM orders 
            GROUP BY platform, internal_status 
            ORDER BY platform, internal_status
        '''))
        rows = result.fetchall()
        
        print("\n=== Orders by Platform and Status ===\n")
        print(f"{'Platform':<12} | {'Status':<20} | {'Count':>8}")
        print("-" * 50)
        
        current_platform = None
        platform_total = 0
        
        for r in rows:
            if current_platform and current_platform != r[0]:
                print(f"{'':12} | {'TOTAL':<20} | {platform_total:>8}")
                print("-" * 50)
                platform_total = 0
            
            current_platform = r[0]
            platform_total += r[2]
            print(f"{r[0]:<12} | {r[1]:<20} | {r[2]:>8}")
        
        # Print last platform total
        if current_platform:
            print(f"{'':12} | {'TOTAL':<20} | {platform_total:>8}")
        
        break

asyncio.run(main())
