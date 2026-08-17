"""
MCP Server — Local Database.

Exposes database operations as MCP tools: querying characters,
inserting locations, and inserting characters with relationships.
"""

import asyncio
import logging

from fastmcp import FastMCP
from sqlmodel import select

from db import get_session, init_db
from models import Character, Location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP-DB] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

server = FastMCP("mcp_db")


@server.tool()
def get_character_by_name(nombre: str):
    """Looks up a character by name in the local database."""
    logger.info("DB lookup: %s", nombre)

    with get_session() as session:
        statement = select(Character).where(Character.name == nombre)
        character = session.exec(statement).first()

        if character:
            logger.info("Found '%s' in local DB", nombre)
        else:
            logger.info("'%s' not found in local DB", nombre)

        return character


@server.tool()
def insert_location_if_not_exists(nombre_planeta: str):
    """Inserts a planet into the DB if it doesn't already exist. Returns the location."""
    logger.info("Checking location: %s", nombre_planeta)

    with get_session() as session:
        statement = select(Location).where(Location.name == nombre_planeta)
        location = session.exec(statement).first()

        if not location:
            location = Location(name=nombre_planeta)
            session.add(location)
            session.commit()
            session.refresh(location)
            logger.info("Inserted new location: %s (id: %d)", nombre_planeta, location.id)
        else:
            logger.info("Location '%s' already exists (id: %d)", nombre_planeta, location.id)

        return location


@server.tool()
def insert_character(personaje: dict, location: dict):
    """
    Inserts a character into the DB with a relationship to their origin planet.
    If the planet doesn't exist yet, it is created first.
    """
    logger.info("Inserting character: %s", personaje.get("name"))

    with get_session() as session:
        location_id = None
        planet_name = location.get("name")

        # Resolve or create the origin planet
        if planet_name and planet_name != "No Planet":
            statement = select(Location).where(Location.name == planet_name)
            loc = session.exec(statement).first()

            if not loc:
                loc = Location(name=planet_name)
                session.add(loc)
                session.commit()
                session.refresh(loc)
                logger.info("Created planet: %s (id: %d)", planet_name, loc.id)

            location_id = loc.id

        new_character = Character(
            name=personaje["name"],
            race=personaje.get("race"),
            gender=personaje.get("gender"),
            ki=personaje.get("ki"),
            max_ki=personaje.get("maxKi"),
            affiliation=personaje.get("affiliation"),
            origin_location_id=location_id
        )

        session.add(new_character)
        session.commit()
        session.refresh(new_character)
        logger.info("Inserted character: %s (id: %d)", new_character.name, new_character.id)

        return new_character


if __name__ == "__main__":
    init_db()
    asyncio.run(server.run_http_async(host="127.0.0.1", port=8001))