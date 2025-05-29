from pydantic import BaseModel
from typing import List, Optional


class AddToCartRequest(BaseModel):
    user_id: str
    product_id: str
    product_url: str
    quantity: Optional[int] = 1

class QueryRequest(BaseModel):
    question: str
    top_k: int = 3
    source_type: str  # "informacion" or "productos"
    expanded_terms: Optional[List[str]] = []

class QueryResponse(BaseModel):
    top_answer: str
    context: List[str]
    source: str
    question: str

class HistoryRecord(BaseModel):
    subscriber_id: str
    question: str
    answer: str
    product_ids: List[str] = []

class SuccessResponse(BaseModel):
    status: str

class ViewCartRequest(BaseModel):
    user_id: str

class CartItem(BaseModel):
    product_id: str
    product_url: str
    quantity: int

class ViewCartResponse(BaseModel):
    session_id: int
    items: List[CartItem]