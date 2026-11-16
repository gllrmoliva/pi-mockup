from fastapi import APIRouter

from app.api.routes import meta
from app.modules.auth.router import router as auth_router
from app.modules.deliverables.router import router as deliverables_router
from app.modules.projects.router import router as projects_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(deliverables_router)
api_router.include_router(meta.router)
