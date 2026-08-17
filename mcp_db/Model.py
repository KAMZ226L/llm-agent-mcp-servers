"""
Database Models.

Defines the data schema using SQLModel (SQLAlchemy + Pydantic).
Two entities with a one-to-many relationship:
- Location: a planet (one planet has many characters)
- Character: a character with a foreign key to their origin planet
"""

from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class Location(SQLModel, table=True):
    """Represents a planet or location in the Dragon Ball universe."""

    id: Optional[int] = Field(default=None, primary_key=True)
    api_id: Optional[int] = Field(default=None, index=True)
    name: str
    description: Optional[str] = None
    is_destroyed: Optional[bool] = None

    characters: List["Character"] = Relationship(back_populates="origin")


class Character(SQLModel, table=True):
    """Represents a Dragon Ball character with a relationship to their origin planet."""

    id: Optional[int] = Field(default=None, primary_key=True)
    api_id: Optional[int] = Field(default=None, index=True)
    name: str
    ki: Optional[str] = None
    max_ki: Optional[str] = None
    race: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    affiliation: Optional[str] = None

    origin_location_id: Optional[int] = Field(default=None, foreign_key="location.id")
    origin: Optional[Location] = Relationship(back_populates="characters")