
import asyncio
from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service
import json

async def test_order_detail():
    db = SessionLocal()
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    client = integration_service.get_client_for_config(config)
    
    order_id = "1074612168319082"
    print(f"Fetching detail for Lazada order {order_id}...")
    try:
        detail = await client.get_order_detail(order_id)
        print("API Response:")
        print(json.dumps(detail, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_order_detail())
