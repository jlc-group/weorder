from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class ReturnItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    condition: str = Field(..., pattern="^(GOOD|DAMAGED)$")
    reason: Optional[str] = None

class ReturnRequest(BaseModel):
    items: List[ReturnItem]
    note: Optional[str] = None
