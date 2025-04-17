from fastapi import FastAPI
from DBInformacionMaestri import DBInformacionMaestri_router

app = FastAPI()

# You can mount other routers too, for other endpoints in the future
app.include_router(DBInformacionMaestri_router, prefix="/maestri", tags=["Maestri"])

@app.get("/")
def root():
    return {"message": "Main API Root"}
