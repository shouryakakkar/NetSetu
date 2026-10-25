"""
Async MongoDB client via Motor.
Collections:
  - raw_configs        : original sanitized upload text
  - normalized_configs : SecurityBaselineModel JSON per job
  - compliance_scans   : full compliance findings per scan
  - pending_review     : unknown syntax items flagged for AI training
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the singleton Motor client (created on first call)."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_url)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the application database handle."""
    return get_mongo_client()[settings.mongo_db]


async def close_mongo_client() -> None:
    """Close the Motor client on app shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


# ── Collection accessors ──────────────────────────────────────────────────────

def raw_configs_col():
    return get_mongo_db()["raw_configs"]


def normalized_configs_col():
    return get_mongo_db()["normalized_configs"]


def compliance_scans_col():
    return get_mongo_db()["compliance_scans"]


def pending_review_col():
    return get_mongo_db()["pending_review"]
