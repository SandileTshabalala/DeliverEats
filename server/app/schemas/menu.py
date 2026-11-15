from pydantic import BaseModel, Field, model_validator

# Limits for dish options (also used by app.services.menu_options)
MAX_GROUPS = 10
MAX_CHOICES = 20
from decimal import Decimal
from typing import List, Optional   
from app.schemas.menu_item import MenuItemRead

class MenuBase(BaseModel):
    name: str

class MenuCreate(BaseModel):
    restaurant_id: str

class OptionChoice(BaseModel):
    id: Optional[str] = Field(default=None, max_length=20)
    name: str = Field(min_length=1, max_length=60)
    # added to the dish price; 0 = free choice (e.g. spice level)
    price: Decimal = Field(default=Decimal("0"), ge=0, le=10000)
    available: bool = True


class OptionGroup(BaseModel):
    """'Spice level': choose 1 of 3. 'Extras': choose up to 4 (or none)."""
    id: Optional[str] = Field(default=None, max_length=20)
    name: str = Field(min_length=1, max_length=40)
    min_select: int = Field(default=0, ge=0, le=MAX_CHOICES)
    max_select: int = Field(default=1, ge=1, le=MAX_CHOICES)
    choices: List[OptionChoice] = Field(min_length=1, max_length=MAX_CHOICES)

    @model_validator(mode="after")
    def sensible_limits(self):
        if self.min_select > self.max_select:
            raise ValueError(f"'{self.name}': the customer cannot be asked for more choices than they may pick")
        if self.max_select > len(self.choices):
            self.max_select = len(self.choices)
        if self.min_select > len(self.choices):
            raise ValueError(f"'{self.name}' asks for more choices than it has")
        return self


Section = Optional[str]


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price: Decimal = Field(gt=0)
    image_url: Optional[str] = None
    section: Optional[str] = Field(default=None, max_length=40)
    options: List[OptionGroup] = Field(default_factory=list, max_length=MAX_GROUPS)


class MenuItemUpdate(BaseModel):
    """Only these fields can be edited (the old endpoint accepted any column)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    section: Optional[str] = Field(default=None, max_length=40)
    options: Optional[List[OptionGroup]] = Field(default=None, max_length=MAX_GROUPS)

    class Config:
        extra = "forbid"

class MenuItemResponse(MenuItemCreate):
    id: str
    is_available: bool
    options: List[OptionGroup] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def no_options_stored(cls, data):
        # items made before options existed have NULL there
        if not isinstance(data, dict) and getattr(data, "options", None) is None:
            return {**{k: getattr(data, k, None) for k in ("id", "name", "description", "price", "image_url", "section", "is_available")}, "options": []}
        if isinstance(data, dict) and data.get("options") is None:
            return {**data, "options": []}
        return data

    class Config:
        from_attributes = True

class MenuRead(MenuBase):
    id: str
    items: List[MenuItemRead] = []

    class Config:
        from_attributes = True

class MenuUpdate(BaseModel):
    name: Optional[str] = None