
from fastapi import FastAPI

app = FastAPI(
    title="ParkSight AI API",
    description="CCTV-powered parking occupancy intelligence",
    version="0.1.0",
)


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "service": "parksight-api",
        "version": "0.1.0",
    }
