from fastapi import APIRouter, HTTPException
from LoadData.service import get_all_products, get_rows_sheet_products
from pydantic import BaseModel
from typing import List, Dict, Any

load_data_router = APIRouter()

class RowsPayload(BaseModel):
    rows: List[Dict[str, Any]]

@load_data_router.post("/sync-products")
def sync_products():
    try:
        result = get_all_products()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()  # 👈 prints full error to Docker logs
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
@load_data_router.post("/sheet-products")
async def sheet_products(payload: RowsPayload):
    try:
        df = get_rows_sheet_products(payload.rows)
        return {
            "status":         "success",
            "rows_received":  len(payload.rows),
            "rows_processed": len(df),
            # uncomment if you want to inspect the processed data:
            # "data": df.to_dict(orient="records")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()  # 👈 prints full error to Docker logs
        raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")