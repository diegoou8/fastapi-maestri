from fastapi import APIRouter, HTTPException, Request
from LoadData.service import get_all_products, get_rows_sheet_products,sync_items_individually, sync_knowledge_from_sheet
import json
from typing import List, Dict, Any
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
    Accepts:
      { "rows": […] }
      { "body": "{\"rows\":[…]}" }  (n8n stringifies it)
      { "body": { "rows": […] } }     (n8n object wrapper)
    """
    try:
        payload = await request.json()

        # 1) If n8n wrapped as "body": "<stringified JSON>"
        if isinstance(payload, dict) and "body" in payload:
            body = payload["body"]
            if isinstance(body, str):
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=422,
                        detail="Invalid JSON in `body` string"
                    )
            elif isinstance(body, dict):
                payload = body

        # 2) Extract and validate rows
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise HTTPException(422, detail="Invalid payload: missing `rows` array")

        # 3) Process into DataFrame
        df = get_rows_sheet_products(rows)
        count = sync_items_individually(df)

        return {
            "status":         "success",
            "rows_received":  len(rows),
            "rows_processed": len(df),
            "updated_count": count
        }

    except HTTPException:
        raise  # re-throw validation errors
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")

@load_data_router.post("/sync-knowledge")
def sync_knowledge():
    try:
        result = sync_knowledge_from_sheet()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Knowledge sync failed: {str(e)}")