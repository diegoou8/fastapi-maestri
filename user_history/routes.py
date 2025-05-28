from fastapi import APIRouter
from user_history.service import ensure_collection_exists, log_interaction
from models.schemas import HistoryRecord

router = APIRouter()

@router.post("/log_user_history")
def log_user_history(record: HistoryRecord):
    return log_interaction(record)

# 👇 Export the router with the expected name
user_history_router = router
