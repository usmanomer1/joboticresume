from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Simple health check app that starts immediately
health_app = FastAPI()

@health_app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "version": "1.0.0"})

@health_app.get("/")
async def root():
    return JSONResponse({"status": "healthy", "service": "Resume Optimizer API"})