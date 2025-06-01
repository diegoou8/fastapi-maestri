from fastapi import APIRouter, HTTPException
from LoadData.service import get_all_products

load_data_router = APIRouter()

@load_data_router.post("/sync-products")
def sync_products():
    try:
        result = get_all_products()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
