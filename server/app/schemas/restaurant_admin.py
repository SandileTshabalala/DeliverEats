from pydantic import BaseModel
from app.schemas.user import UserRead
from app.schemas.restaurant import RestaurantRead

class RestaurantAdminBase(BaseModel):
    user_id: str
    restaurant_id: str

class RestaurantAdminCreate(RestaurantAdminBase):
    pass

class RestaurantAdminRead(RestaurantAdminBase):
    class Config:
        from_attributes = True

class RestaurantAdminDetail(BaseModel):
    user: UserRead
    restaurant: RestaurantRead

    class Config:
        from_attributes = True