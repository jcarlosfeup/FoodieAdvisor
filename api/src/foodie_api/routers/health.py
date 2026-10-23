import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from foodie_api.dependencies import get_repository
from foodie_api.repository import Repository
from foodie_api.schemas import Health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=Health)
def live() -> Health:
    """The process is up. Used by container liveness probes; never touches the database."""
    return Health(status="ok")


@router.get(
    "/ready", response_model=Health, responses={503: {"description": "Database or mart not available"}}
)
def ready(repository: Annotated[Repository, Depends(get_repository)]) -> Health:
    """The database is reachable and the mart tables exist."""
    try:
        is_ready = repository.is_ready()
    except Exception:
        logger.exception("readiness check failed")
        is_ready = False
    if not is_ready:
        raise HTTPException(status_code=503, detail="database or mart schema not available")
    return Health(status="ready")
