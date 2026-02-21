from fastapi import APIRouter

from app.nudge_scheduler import run_nudge_scan

router = APIRouter(prefix="/api/nudge", tags=["nudge"])


@router.post("/run")
async def trigger_nudge_scan() -> dict:
    result = await run_nudge_scan()
    return result
