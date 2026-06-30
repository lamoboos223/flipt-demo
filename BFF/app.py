from fastapi import FastAPI

from routes import router

app = FastAPI(
    title="Flipt BFF",
    description="Batch-evaluates all flags in a namespace with caching for mobile clients.",
    version="1.0.0",
)
app.include_router(router)
