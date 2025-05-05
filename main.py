from fastapi import FastAPI
from DBInformacionMaestri import DBInformacionMaestri_router
from log_user_history import router as LogUserHistoryRouter  # ✅ Add this line

app = FastAPI()

# Include both routers
app.include_router(DBInformacionMaestri_router, prefix="/maestri", tags=["Maestri"])
app.include_router(LogUserHistoryRouter, prefix="/maestri", tags=["UserHistory"])  # ✅ Register this too

@app.get("/")
def root():
    return {"message": "Main API Root"}
