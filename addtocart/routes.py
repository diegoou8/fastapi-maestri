from fastapi import APIRouter, HTTPException
from models.schemas import AddToCartRequest
from addtocart.service import add_product_to_cart

addtocart_router = APIRouter()

@addtocart_router.post("/add-to-cart")
def add_to_cart(request: AddToCartRequest):
    try:
        add_product_to_cart(
            user_id=request.user_id,
            product_id=request.product_id,
            product_url=request.product_url,
            quantity=request.quantity
        )
        return {"message": "Product updated in cart successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
