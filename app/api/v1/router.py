from fastapi import APIRouter

from app.api.v1.endpoints import tenants, workspaces, teammates, assistants, knowledge, orchestration

router = APIRouter()

router.include_router(tenants.router)
router.include_router(workspaces.router)
router.include_router(teammates.router)
router.include_router(assistants.router)
router.include_router(knowledge.router)
router.include_router(orchestration.router)
