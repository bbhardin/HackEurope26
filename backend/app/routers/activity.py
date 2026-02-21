from typing import Optional

from fastapi import APIRouter, Query

from app.crud import get_agent_actions

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("")
async def list_activity(
    agent_type: Optional[str] = Query(None),
    limit: int = Query(50),
) -> list[dict]:
    return get_agent_actions(limit=limit, agent_type=agent_type)
