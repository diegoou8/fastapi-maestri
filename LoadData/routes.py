from fastapi import APIRouter, HTTPException, Request
from LoadData.service import get_all_products, get_rows_sheet_products

load_data_router = APIRouter()


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
async def sheet_products(request: Request):
    """
    Accepts JSON in any of these shapes:
      { "rows": [ … ] }
      { "body": { "rows": [ … ] } }
    """
    try:
        payload = await request.json()

        # 1) Unwrap if your n8n is nesting under "body"
        if isinstance(payload, dict) and "body" in payload:
            payload = payload["body"]

        # 2) Extract rows and validate
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise HTTPException(
                status_code=422,
                detail="Invalid payload: missing `rows` array"
            )

        # 3) Process
        df = get_rows_sheet_products(rows)

        return {
            "status":         "success",
            "rows_received":  len(rows),
            "rows_processed": len(df),
        }

    except HTTPException:
        # re-raise our validation errors
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")