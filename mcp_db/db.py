"""
Database Connection.

Manages the PostgreSQL connection and session lifecycle using SQLModel.
Connection URL is loaded from environment variables.
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost/dragonball"
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Creates all tables defined in the SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """Yields a database session with automatic cleanup."""
    with Session(engine) as session:
        yield session