from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class RestaurantAdmin(Base):
    __tablename__ = "restaurant_admins"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    restaurant_id = Column(String, ForeignKey("restaurants.id", ondelete="CASCADE"))

    #relationships
        # optional relationships (recommended)
    user = relationship("User", backref="managed_restaurants")
    restaurant = relationship("Restaurant", backref="admins")

    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_restaurant_admin"),
    )