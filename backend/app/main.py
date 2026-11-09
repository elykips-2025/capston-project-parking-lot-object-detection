
from fastapi import FastAPI
from fastapi import HTTPException
from sqlalchemy import text

from app.core.database import engine
from app.api.auth import router as auth_router
from app.api.parking_sites import router as parking_sites_router
from app.api.cameras import router as cameras_router
from app.api.video_recordings import router as video_recordings_router
from app.api.occupancy import router as occupancy_router


app = FastAPI(
    title="ParkSight AI API",
    description="CCTV-powered parking occupancy intelligence",
    version="0.1.0",
)



app.include_router(
    parking_sites_router,
    prefix="/api/v1",
)


app.include_router(
    cameras_router,
    prefix="/api/v1",
)


app.include_router(
    video_recordings_router,
    prefix="/api/v1",
)

app.include_router(
    occupancy_router,
    prefix="/api/v1",
)




@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "service": "parksight-api",
        "version": "0.1.0",
    }


@app.get("/api/v1/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "postgresql",
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

app.include_router(
    auth_router,
    prefix="/api/v1",
)
