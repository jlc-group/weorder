
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uuid
from typing import List, Optional

from app.models.prepack import PrepackBox, PrepackBoxItem
from app.models.master import Warehouse
from app.models.product import Product

class PrepackService:
    
    @staticmethod
    def create_batch(
        db: Session,
        warehouse_id: str,
        items: List[dict], # [{"product_id": ..., "sku": ..., "quantity": ...}]
        quantity: int,
        created_by_id: Optional[str] = None
    ) -> List[PrepackBox]:
        """
        Create a batch of pre-pack boxes
        """
        created_boxes = []
        
        # Generate base ID using timestamp
        # Format: PK{YYMMDD}-{HHMMSS}-{Random}
        # Not using sequence for simplicity/speed
        base_prefix = f"PK{datetime.now().strftime('%y%m%d%H%M')}"
        
        for i in range(quantity):
            # Unique UID per box
            suffix = str(uuid.uuid4())[:6].upper()
            box_uid = f"{base_prefix}-{suffix}"
            
            # Create Box
            box = PrepackBox(
                box_uid=box_uid,
                warehouse_id=warehouse_id,
                status="PREPACK_READY",
                last_modified_by=created_by_id,
                last_modified_at=datetime.now()
            )
            db.add(box)
            db.flush() # Flush to get box ready for items check
            
            # Add Items
            for item_data in items:
                item = PrepackBoxItem(
                    box_uid=box_uid,
                    product_id=item_data["product_id"],
                    sku=item_data["sku"],
                    quantity=item_data["quantity"],
                    line_type="NORMAL"
                )
                db.add(item)
            
            created_boxes.append(box)
            
        db.commit()
        return created_boxes

    @staticmethod
    def get_available_boxes(db: Session, sku: str = None) -> List[dict]:
        """
        Get counts of available pre-pack boxes grouped by content
        (Simplified version: just checking main SKU for now)
        """
        query = db.query(PrepackBox).filter(PrepackBox.status == "PREPACK_READY")
        
        if sku:
            query = query.join(PrepackBoxItem).filter(PrepackBoxItem.sku == sku)
            
        return query.all()
