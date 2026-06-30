from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import router

app = FastAPI(title="MarketPlace App1")
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")
