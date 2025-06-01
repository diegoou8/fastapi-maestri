from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi import FastAPI
from DBInformacionMaestri.routes import DBInformacionMaestri_router
from addtocart.routes import addtocart_router
from user_history.routes import user_history_router
from LoadData.routes import load_data_router

# ✅ Always load from repo root, regardless of where the file is run from
def load_env():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dotenv_path = os.path.join(root_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        None

load_env()

# Create app
app = FastAPI()

# Include routers
app.include_router(DBInformacionMaestri_router, prefix="/maestri", tags=["Maestri"])
app.include_router(addtocart_router, prefix="/cart", tags=["Cart"])
app.include_router(user_history_router, prefix="/user", tags=["User History"])
app.include_router(load_data_router, prefix="/load", tags=["Load Data"])

@app.get("/")
def root():
    return {"message": "FastAPI Maestri Root"}
