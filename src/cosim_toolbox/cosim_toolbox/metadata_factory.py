"""
Factory for creating metadata managers.
"""

from typing import Any
from .base_metadata import BaseMetadataManager


def create_metadata_manager(
    backend: str, location: str, **kwargs
) -> BaseMetadataManager:
    """
    Factory function to create appropriate metadata manager.

    Args:
        backend (str): Backend type ("json", "mongo")
        location (str): Storage location (path for JSON, URI for MongoDB)
        **kwargs: Backend-specific options
            - db_name (str): Database name for MongoDB (default: "cst")

    Returns:
        BaseMetadataManager: Configured metadata manager

    Raises:
        ValueError: If backend is not supported
        ImportError: If required dependencies are missing
    """
    backend = backend.lower()

    if backend == "json":
        from .json_metadata import JSONMetadataManager

        return JSONMetadataManager(location)
    elif backend == "mongo":
        from .mongo_metadata import MongoMetadataManager

        db_name = kwargs.get("db_name", "cst")
        return MongoMetadataManager(location, db_name)
    else:
        raise ValueError(f"Unknown backend: {backend}. Supported: json, mongo")


# Convenience functions
def create_json_manager(location: str) -> "JSONMetadataManager":
    """Create JSON metadata manager."""
    return create_metadata_manager("json", location)


def create_mongo_manager(location: str, db_name: str = "cst") -> "MongoMetadataManager":
    """Create MongoDB metadata manager."""
    return create_metadata_manager("mongo", location, db_name=db_name)
