from fastapi import APIRouter
from api.auth.router import auth_router
from api.expenses.router import expenses_router
from api.commiter.router import commiter_router
from api.labfile.router import labfile_router
from api.notes.router import notes_router
from api.taskmanager.router import taskmanager_router
from api.tracking.router import tracking_router
from api.vibelist.router import vibelist_router
api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(expenses_router, prefix="/expenses", tags=["Expences"])
api_router.include_router(commiter_router, prefix="/commiter", tags=["Commiter"])
api_router.include_router(labfile_router, prefix="/labfile", tags=["Labfile"])
api_router.include_router(notes_router, prefix="/notes", tags=["Notes"])
api_router.include_router(taskmanager_router, prefix="/taskmanager", tags=["Taskmanager"])
api_router.include_router(tracking_router, prefix="/tracking", tags=["Tracking"])
api_router.include_router(vibelist_router, prefix="/vibelist", tags=["Vibelist"])