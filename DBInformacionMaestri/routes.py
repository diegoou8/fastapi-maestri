from fastapi import APIRouter, HTTPException
from models.schemas import QueryRequest, QueryResponse
from DBInformacionMaestri.service import initialize_model, run_query
import logging
import traceback

DBInformacionMaestri_router = APIRouter()

@DBInformacionMaestri_router.on_event("startup")
def load_model():
    initialize_model()

@DBInformacionMaestri_router.get("/")
def read_root():
    return {"message": "FastAPI Maestri is live!"}

@DBInformacionMaestri_router.post("/query", response_model=QueryResponse)
def query_qdrant(request: QueryRequest):
    try:
        return run_query(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error("Exception occurred:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
