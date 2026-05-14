from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.restaurant import RestaurantCreate, RestaurantResponse
from app.services.restaurant_service import create_restaurant, get_restaurants, get_restaurant
from app.core.dependencies import require_role, get_current_user,get_db
from app.core.roles import Role


from app.schemas.order import OrderRead
from app.services.order_service import get_restaurant_orders
from app.models.restaurant import Restaurant

router = APIRouter(
    tags=["Restaurant"]
)

@router.get("/", response_model=list[RestaurantResponse])
async def list_restaurants(db: Session = Depends(get_db)):
    return await get_restaurants(db)

@router.get("/orders", response_model=list[OrderRead])
def restaurant_orders(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user = Depends(require_role(Role.RESTAURANT_ADMIN))
):
    # Find restaurant owned by this admin
    restaurant = db.query(Restaurant).filter(Restaurant.admin_id == user.id).first()
    if not restaurant:
        return []
    
    return get_restaurant_orders(db, restaurant.id, limit=limit, offset=offset)

@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant_route(restaurant_id: str, db: Session = Depends(get_db)):
    out = await get_restaurant(db, restaurant_id)
    if not out:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return out

@router.post("/", response_model=RestaurantResponse)
def create_restaurant_route(payload: RestaurantCreate, db: Session = Depends(get_db), current_user=Depends(require_role(Role.SUPER_ADMIN))):
    return create_restaurant(db, payload)
