from fastapi import APIRouter, HTTPException

from app.crud import get_alerts, acknowledge_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(acknowledged: bool = False) -> list[dict]:
    return get_alerts(acknowledged=acknowledged)


@router.post("/{alert_id}/acknowledge")
async def ack_alert(alert_id: str) -> dict[str, str]:
    if acknowledge_alert(alert_id):
        return {"status": "acknowledged"}
    raise HTTPException(status_code=404, detail="Alert not found")
