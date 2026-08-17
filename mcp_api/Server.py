"""
MCP Server — External API.

Exposes Dragon Ball API data as MCP tools.
The LLM agent calls these tools when data is not found in the local database.
"""

import logging

import requests
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP-API] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

API_BASE_URL = "https://dragonball-api.com/api/characters"

server = FastMCP("mcp_api")


@server.tool()
def get_character_from_api(nombre: str):
    """Fetches a character by name from the Dragon Ball API."""
    try:
        nombre = nombre.capitalize()
        logger.info("Querying API for: %s", nombre)

        response = requests.get(f"{API_BASE_URL}?name={nombre}", timeout=10)

        if response.status_code != 200:
            logger.warning("API returned status %d", response.status_code)
            return None

        data = response.json()

        if not data or len(data) == 0:
            logger.info("Character '%s' not found in API", nombre)
            return None

        character = data[0]
        origin_planet = character.get("originPlanet")

        result = {
            "name": character.get("name"),
            "race": character.get("race"),
            "gender": character.get("gender"),
            "ki": character.get("ki"),
            "maxKi": character.get("maxKi"),
            "affiliation": character.get("affiliation"),
            "originPlanet": origin_planet.get("name") if origin_planet else None
        }

        logger.info("Found: %s (planet: %s)", result["name"], result["originPlanet"])
        return result

    except requests.Timeout:
        logger.error("API request timed out")
        return None
    except Exception as e:
        logger.error("Error querying API: %s", e)
        return None


if __name__ == "__main__":
    server.run(transport="streamable-http", host="127.0.0.1", port=8002)