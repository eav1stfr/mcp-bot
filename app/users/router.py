from fastapi import APIRouter

from app.users.dependencies import ActorDep, SvcDep
from app.users.schemas import CoupleRetrieve

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/me", summary="The caller and their partner")
def get_me(svc: SvcDep, actor: ActorDep) -> CoupleRetrieve:
    return svc.get_couple(actor)
