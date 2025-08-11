"""
MongoDB-based metadata management for CoSim Toolbox.
"""

import logging
from typing import Any, Dict, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from .base_metadata import BaseMetadataManager

logger = logging.getLogger(__name__)


class MongoMetadataManager(BaseMetadataManager):
    """MongoDB-based metadata manager."""

    def __init__(self, location: str, db_name: str = "cst"):
        super().__init__(location)
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )

        self.uri = location
        self.db_name = db_name
        self.client = None
        self.db = None
        self._cst_name_field = "cst_name"  # Field name for document identification

    def _get_collection(self, collection_type: str):
        """Get MongoDB collection object."""
        if collection_type == "federations":
            return self.db.federations
        elif collection_type == "scenarios":
            return self.db.scenarios
        else:
            # Custom collection
            return self.db[collection_type]

    def _write_data(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Write document to MongoDB."""
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return False

        try:
            self._validate_name(name)

            coll = self._get_collection(collection_type)

            # Check if document exists
            existing = coll.find_one({self._cst_name_field: name})
            if existing and not overwrite:
                logger.error(
                    f"{collection_type.title()} '{name}' already exists and overwrite=False"
                )
                return False

            # Prepare document with our identification field
            document = data.copy()
            document[self._cst_name_field] = name

            if existing and overwrite:
                # Update existing document
                result = coll.replace_one({self._cst_name_field: name}, document)
                success = result.modified_count > 0
            else:
                # Insert new document
                result = coll.insert_one(document)
                success = result.inserted_id is not None

            if success:
                logger.debug(f"{collection_type.title()} '{name}' written to MongoDB")
            else:
                logger.error(f"Failed to write {collection_type} '{name}' to MongoDB")

            return success

        except ValueError as e:
            logger.error(f"Invalid name: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to write {collection_type} '{name}': {e}")
            return False

    def _read_data(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Read document from MongoDB."""
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return None

        try:
            self._validate_name(name)

            coll = self._get_collection(collection_type)
            document = coll.find_one({self._cst_name_field: name})

            if not document:
                logger.warning(
                    f"{collection_type.title()} '{name}' not found in MongoDB"
                )
                return None

            # Remove MongoDB internal fields
            document.pop("_id", None)
            document.pop(self._cst_name_field, None)

            logger.debug(f"{collection_type.title()} '{name}' read from MongoDB")
            return document

        except ValueError as e:
            logger.error(f"Invalid name: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read {collection_type} '{name}': {e}")
            return None

    def _delete_data(self, collection_type: str, name: str) -> bool:
        """Delete document from MongoDB."""
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return False

        try:
            self._validate_name(name)

            coll = self._get_collection(collection_type)
            result = coll.delete_one({self._cst_name_field: name})

            if result.deleted_count > 0:
                logger.debug(f"{collection_type.title()} '{name}' deleted from MongoDB")
                return True
            else:
                logger.warning(
                    f"{collection_type.title()} '{name}' not found for deletion"
                )
                return False

        except ValueError as e:
            logger.error(f"Invalid name: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete {collection_type} '{name}': {e}")
            return False

    def _list_data(self, collection_type: str) -> list[str]:
        """List document names in a collection."""
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return []

        try:
            coll = self._get_collection(collection_type)
            cursor = coll.find({}, {self._cst_name_field: 1})

            names = []
            for doc in cursor:
                if self._cst_name_field in doc:
                    names.append(doc[self._cst_name_field])

            return sorted(names)

        except Exception as e:
            logger.error(f"Failed to list {collection_type}: {e}")
            return []

    def _list_collections(self) -> list[str]:
        """List available custom collection names."""
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return []

        try:
            # Get all collection names and filter out standard ones
            all_collections = self.db.list_collection_names()
            custom_collections = [
                name
                for name in all_collections
                if name not in ["federations", "scenarios"]
            ]
            return sorted(custom_collections)
        except Exception as e:
            logger.error(f"Failed to list custom collections: {e}")
            return []

    def connect(self) -> bool:
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)

            # Test the connection
            self.client.admin.command("ping")

            self.db = self.client[self.db_name]
            self._is_connected = True

            logger.info(
                f"MongoDB metadata manager connected to: {self.uri}/{self.db_name}"
            )
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
        self._is_connected = False
        logger.debug("MongoDB metadata manager disconnected")
