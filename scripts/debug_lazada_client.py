
import asyncio
import logging
from app.core.database import SessionLocal
from app.models.integration import PlatformConfig
from app.services import integration_service
import json
import sys

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("api_debug")

async def debug_lazada():
    db = SessionLocal()
    config = db.query(PlatformConfig).filter(PlatformConfig.platform == 'lazada', PlatformConfig.is_active == True).first()
    
    # Manually initialize client to control timeouts if needed, 
    # but first let's try the standard one with logging.
    logger.info("Initializing Lazada client...")
    client = integration_service.get_client_for_config(config)
    
    order_id = "1074612168319082"
    logger.info(f"Attempting to fetch order {order_id}...")
    
    try:
        # We'll use a timeout to avoid forever-hang
        # Note: LazadaClient uses internal httpx.AsyncClient() without explicit timeout in its methods
        # but we can wrap it in asyncio.wait_for
        detail = await asyncio.wait_for(client.get_order_detail(order_id), timeout=20.0)
        logger.info("Success! API Response received.")
        print(json.dumps(detail, indent=2))
    except asyncio.TimeoutError:
        logger.error("Request timed out after 20 seconds")
    except Exception as e:
        logger.error(f"Error during API call: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_lazada())
