"""Database models and schema management for Chat-O-Llama."""

from utils.database import init_db


def init_database_schema():
    """Initialize the database schema."""
    init_db()