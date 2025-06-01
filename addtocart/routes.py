from fastapi import APIRouter, HTTPException
from models.schemas import AddToCartRequest, RemoveFromCartRequest, CreateCartRequest
from addtocart.service import add_product_to_cart, remove_product_from_cart, create_cart_session,foxycart_payload
from models.schemas import ViewCartRequest, ViewCartResponse
from addtocart.service import get_cart_contents, foxycart_payload


addtocart_router = APIRouter()

@addtocart_router.post("/add-to-cart")
def add_to_cart(request: AddToCartRequest):
    return add_product_to_cart(
        user_id=request.user_id,
        product_id=request.product_id,
        product_url=request.product_url,
        quantity=request.quantity
        price=request.price,
        url_imagen=request.url_imagen
    )

@addtocart_router.post("/remove-from-cart")
def remove_from_cart(request: RemoveFromCartRequest):
    return remove_product_from_cart(
        user_id=request.user_id,
        product_id=request.product_id
    )

@addtocart_router.post("/create-cart-session")
def create_session(request: CreateCartRequest):
    session_id = create_cart_session(request.user_id)
    return {"session_id": session_id}

@addtocart_router.post("/view-cart", response_model=ViewCartResponse)
def view_cart(request: ViewCartRequest):
    return get_cart_contents(request.user_id)

@addtocart_router.get("/foxycart-payload")
def get_foxycart_checkout_url(user_id: str):
    return foxycart_payload(user_id)
