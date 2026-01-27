"""
Label Service - Handle logic for retrieving and merging shipping labels
"""
import io
import httpx
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from pypdf import PdfWriter, PdfReader

from app.services import OrderService, integration_service
from app.models import OrderHeader
from app.integrations import TikTokClient, ShopeeClient, LazadaClient

logger = logging.getLogger(__name__)

class LabelService:
    @staticmethod
    async def generate_batch_labels(db: Session, order_ids: List[str]) -> bytes:
        """
        Generate a merged PDF of shipping labels for the given orders.
        Supports: TikTok, Shopee, Lazada
        """
        merger = PdfWriter()
        client_cache = {}
        
        async with httpx.AsyncClient() as http_client:
            for order_id_str in order_ids:
                try:
                    # Resolve order (support UUID or external ID)
                    try:
                        uuid_obj = UUID(order_id_str)
                        order = OrderService.get_order_by_id(db, uuid_obj)
                    except ValueError:
                        order = OrderService.get_order_by_external_id(db, order_id_str)
                    
                    if not order:
                        logger.warning(f"Order not found for label generation: {order_id_str}")
                        continue
                        
                    # Check platform
                    platform = order.channel_code.lower()
                    
                    # All platforms now supported
                    if platform not in ["tiktok", "shopee", "lazada"]:
                        logger.warning(f"Official label not supported for platform {platform} (Order: {order.external_order_id})")
                        continue
                        
                    # Get Client (cached per platform)
                    if platform not in client_cache:
                        configs = integration_service.get_platform_configs(db, platform=platform, is_active=True)
                        if not configs:
                            logger.error(f"No active configuration found for {platform}")
                            continue
                        config = configs[0] 
                        client_cache[platform] = integration_service.get_client_for_config(config)
                    
                    client = client_cache[platform]
                    
                    # Get Label URL - all clients now have get_shipping_label method
                    label_url = None
                    if hasattr(client, 'get_shipping_label'):
                        label_url = await client.get_shipping_label(order.external_order_id)
                    
                    if not label_url:
                        logger.warning(f"No label URL returned for {order.external_order_id} ({platform})")
                        continue
                        
                    # Download PDF
                    retry_count = 0
                    pdf_content = None
                    while retry_count < 3:
                        try:
                            response = await http_client.get(label_url, timeout=15.0)
                            if response.status_code == 200:
                                pdf_content = response.content
                                break
                        except Exception as e:
                            logger.warning(f"Retry {retry_count+1} downloading label for {order.external_order_id}: {e}")
                        retry_count += 1
                        
                    if pdf_content:
                        # Add to merger
                        pdf_file = io.BytesIO(pdf_content)
                        try:
                            reader = PdfReader(pdf_file)
                            for page in reader.pages:
                                merger.add_page(page)
                        except Exception as e:
                            logger.error(f"Failed to parse PDF for {order.external_order_id}: {e}")
                    else:
                        logger.error(f"Failed to download label for {order.external_order_id}")

                except Exception as e:
                    logger.error(f"Error processing label for {order_id_str}: {e}")
                    continue
        
        # Check if we actually have pages
        if len(merger.pages) == 0:
            logger.warning("No labels were successfully downloaded/merged.")
            return None

        # Write merged PDF to bytes
        output_stream = io.BytesIO()
        merger.write(output_stream)
        msg_bytes = output_stream.getvalue()
        output_stream.close()
        
        return msg_bytes

