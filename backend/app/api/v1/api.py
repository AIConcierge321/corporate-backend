from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, scim

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(scim.router, prefix="/scim/v2", tags=["SCIM"])
