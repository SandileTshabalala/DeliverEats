from fastapi import APIRouter, Depends
from app.core.dependencies import require_role
from app.core.roles import Role

router = APIRouter(
    tags=["Customer"]
)

@router.get("/restaurants")
def list_restaurants(
    user = Depends(require_role(Role.CUSTOMER))
):
    return {"restaurants": []}

@router.get("/orders")
def customer_orders(
    user = Depends(require_role(Role.CUSTOMER))
):
    return {"orders": []}
