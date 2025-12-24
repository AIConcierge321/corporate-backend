from fastapi import APIRouter

from app.api.v1.endpoints import (
    approvals,
    auth,
    bookings,
    destinations,
    health,
    roles,
    scim,
    search,
    trains,
    transfers,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(scim.router, prefix="/scim/v2", tags=["SCIM"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(destinations.router, prefix="/destinations", tags=["Destinations"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["Transfers"])
api_router.include_router(trains.router, prefix="/trains", tags=["Trains"])
