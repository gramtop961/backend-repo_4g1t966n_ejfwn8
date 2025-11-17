"""
Database Schemas for SneakPeak

Each Pydantic model represents a collection in MongoDB. The collection name
is the lowercase of the class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class Design(BaseModel):
    """
    Saved sneaker custom designs
    Collection: design
    """
    userId: Optional[str] = Field(None, description="Associated user id (Supabase uid or anonymous token)")
    sneakerId: str = Field(..., description="Base sneaker id this design is based on")
    name: str = Field(..., description="Friendly name for the design")
    colors: Dict[str, str] = Field(default_factory=dict, description="Map of part->hex color")
    materials: Dict[str, str] = Field(default_factory=dict, description="Map of part->material key")
    laces: Optional[str] = Field(None, description="Lace color/material key")
    pattern: Optional[str] = Field(None, description="Optional pattern key")
    notes: Optional[str] = None


class Alert(BaseModel):
    """
    Price drop or restock alerts
    Collection: alert
    """
    userId: Optional[str] = None
    sneakerId: str
    type: str = Field(..., description="price_drop | restock")
    targetPrice: Optional[float] = Field(None, ge=0)
    size: Optional[str] = None
    email: Optional[str] = None


# Example existing models retained for reference (not used directly):
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True


class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
