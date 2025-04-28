from fastapi import FastAPI
from DBInformacionMaestri import DBInformacionMaestri_router

app = FastAPI()

# Include your router
app.include_router(DBInformacionMaestri_router, prefix="/maestri")