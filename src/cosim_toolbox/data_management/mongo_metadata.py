"""
MongoDB-based metadata management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.
"""

import logging
from typing import Any, Dict, Optional, List

try:
    from pymongo import MongoClient
    from pymongo.database import Database
    from pymongo.collection import Collection
    from pymongo.errors import (
        ConnectionFailure,
        ServerSelectionTimeoutError,
        PyMongoError,
    )

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from .abstractions import (
    MDDataWriter,
    MDDataReader,
    MDDataManager,
)
from .validation import validate_name, ValidationError, safe_name_log

logger = logging.getLogger(__name__)


# +++ A dedicated helper class for managing the MongoDB connection +++
class _MongoConnectionHelper:
    """Manages the connection state and logic for MongoDB."""

    def __init__(self, uri: str, db_name: str):
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )
        self.uri = uri
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.cst_name_field = "cst_name"  # Field name for document identification

    def connect(self) -> bool:
        """Establishes connection to the MongoDB server."""
        if self.client:
            return True  # Already connected
        try:
            validate_name(self.db_name, context="database name")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")  # Test connection
            self.db = self.client[self.db_name]
            logger.info(f"MongoDB helper connected to: {self.uri}/{self.db_name}")
            return True
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return False
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self.client = None
            return False

    def disconnect(self) -> None:
        """Closes the connection to the MongoDB server."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.debug("MongoDB helper disconnected.")

    def get_collection(self, collection_type: str) -> Collection:
        """Gets a collection object from the database."""
        if not self.db:
            raise PyMongoError("Not connected to database.")
        if collection_type == "federations":
            return self.db.federations
        elif collection_type == "scenarios":
            return self.db.scenarios
        else:
            validate_name(collection_type, context="collection name")
            return self.db[collection_type]


# +++ Uses composition ("has-a" conn_helper) instead of inheritance +++
class MongoMetadataWriter(MDDataWriter):
    """MongoDB-based metadata writer."""

    def __init__(
        self,
        *,
        uri: Optional[str] = None,
        db_name: Optional[str] = "cst",
        conn_helper: Optional[_MongoConnectionHelper] = None,
    ):
        """
        Initialize the Mongo writer.

        For standalone use:
            writer = MongoMetadataWriter(uri="mongodb://localhost:27017", db_name="my_db")
        For managed use (by MongoMetadataManager):
            helper = _MongoConnectionHelper(...)
            writer = MongoMetadataWriter(conn_helper=helper)
        """
        super().__init__()
        if conn_helper:
            self.conn_helper = conn_helper
            self._owns_connection = False
        elif uri and db_name:
            self.conn_helper = _MongoConnectionHelper(uri, db_name)
            self._owns_connection = True
        else:
            raise ValueError(
                "Either 'conn_helper' or both 'uri' and 'db_name' must be provided."
            )

    def connect(self) -> bool:
        """Connects to the database, creating the connection if owned."""
        if self._owns_connection:
            if not self.conn_helper.connect():
                return False

        # In both cases, verify the connection exists before setting state
        if self.conn_helper.client:
            self._is_connected = True
            return True
        return False

    def disconnect(self) -> None:
        """Disconnects from the database if the connection is owned."""
        if self._owns_connection:
            self.conn_helper.disconnect()
        self._is_connected = False

    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        return self.write("federations", name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        return self.write("scenarios", name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        if not self.is_connected:
            logger.error("MongoDB writer not connected. Call connect() first.")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            if not isinstance(data, dict):
                raise ValidationError(f"Data must be a dictionary, got {type(data)}")

            coll = self.conn_helper.get_collection(collection_type)
            name_field = self.conn_helper.cst_name_field

            query = {name_field: name}
            existing = coll.find_one(query)

            if existing and not overwrite:
                logger.error(
                    f"{collection_type.title()} '{safe_name_log(name)}' already exists and overwrite=False"
                )
                return False

            document = {**data, name_field: name}

            if existing and overwrite:
                result = coll.replace_one(query, document)
                success = result.modified_count > 0 or result.matched_count > 0
                action = "updated"
            else:
                result = coll.insert_one(document)
                success = result.inserted_id is not None
                action = "inserted"

            if success:
                logger.debug(
                    f"{collection_type.title()} '{safe_name_log(name)}' {action} in MongoDB"
                )
            else:
                logger.error(
                    f"Failed to write {collection_type} '{safe_name_log(name)}' to MongoDB"
                )
            return success
        except (ValidationError, PyMongoError) as e:
            logger.error(
                f"Error writing {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error writing {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False


class MongoMetadataReader(MDDataReader):
    """MongoDB-based metadata reader."""

    def __init__(
        self,
        *,
        uri: Optional[str] = None,
        db_name: Optional[str] = "cst",
        conn_helper: Optional[_MongoConnectionHelper] = None,
    ):
        """
        Initialize the Mongo reader.

        For standalone use:
            reader = MongoMetadataReader(uri="mongodb://localhost:27017", db_name="my_db")
        For managed use (by MongoMetadataManager):
            helper = _MongoConnectionHelper(...)
            reader = MongoMetadataReader(conn_helper=helper)
        """
        super().__init__()
        if conn_helper:
            self.conn_helper = conn_helper
            self._owns_connection = False
        elif uri and db_name:
            self.conn_helper = _MongoConnectionHelper(uri, db_name)
            self._owns_connection = True
        else:
            raise ValueError(
                "Either 'conn_helper' or both 'uri' and 'db_name' must be provided."
            )

    def connect(self) -> bool:
        if self._owns_connection:
            if not self.conn_helper.connect():
                return False
        if self.conn_helper.client:
            self._is_connected = True
            return True
        return False

    def disconnect(self) -> None:
        if self._owns_connection:
            self.conn_helper.disconnect()
        self._is_connected = False

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        return self.read("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        return self.read("scenarios", name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            logger.error("MongoDB reader not connected. Call connect() first.")
            return None
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            coll = self.conn_helper.get_collection(collection_type)
            name_field = self.conn_helper.cst_name_field

            document = coll.find_one({name_field: name})

            if not document:
                logger.debug(
                    f"{collection_type.title()} '{safe_name_log(name)}' not found in MongoDB"
                )
                return None

            document.pop("_id", None)
            document.pop(name_field, None)
            logger.debug(
                f"{collection_type.title()} '{safe_name_log(name)}' read from MongoDB"
            )
            return document
        except (ValidationError, PyMongoError) as e:
            logger.error(
                f"Error reading {collection_type} '{safe_name_log(name)}': {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error reading {collection_type} '{safe_name_log(name)}': {e}"
            )
            return None

    def list_federations(self) -> List[str]:
        return self.list_items("federations")

    def list_scenarios(self) -> List[str]:
        return self.list_items("scenarios")

    def list_items(self, collection_type: str) -> List[str]:
        if not self.is_connected:
            logger.error("MongoDB reader not connected.")
            return []
        try:
            coll = self.conn_helper.get_collection(collection_type)
            name_field = self.conn_helper.cst_name_field

            names = [
                doc[name_field]
                for doc in coll.find({}, {name_field: 1})
                if name_field in doc
            ]
            return sorted(names)
        except (ValidationError, PyMongoError) as e:
            logger.error(f"Error listing {collection_type}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing {collection_type}: {e}")
            return []

    def list_custom_collections(self) -> List[str]:
        if not self.is_connected or not self.conn_helper.db:
            logger.error("MongoDB reader not connected.")
            return []
        try:
            all_collections = self.conn_helper.db.list_collection_names()
            return sorted(
                [
                    name
                    for name in all_collections
                    if name not in ["federations", "scenarios", "system.views"]
                ]
            )
        except PyMongoError as e:
            logger.error(f"MongoDB error listing custom collections: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing custom collections: {e}")
            return []


class MongoMetadataManager(MDDataManager):
    """
    Joint MongoDB metadata manager using composition.
    Manages a shared connection for a single reader and writer instance.
    """

    def __init__(self, uri: str, db_name: str = "cst"):
        super().__init__()
        # The manager creates ONE helper and shares it.
        self.conn_helper = _MongoConnectionHelper(uri, db_name)
        self.writer = MongoMetadataWriter(conn_helper=self.conn_helper)
        self.reader = MongoMetadataReader(conn_helper=self.conn_helper)

    def connect(self) -> bool:
        if not self.conn_helper.connect():
            return False

        # Connect the children (which will just set their internal state)
        self.writer.connect()
        self.reader.connect()
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        self.conn_helper.disconnect()
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def delete_federation(self, name: str) -> bool:
        return self._delete_document("federations", name)

    def delete_scenario(self, name: str) -> bool:
        return self._delete_document("scenarios", name)

    def delete(self, collection_type: str, name: str) -> bool:
        return self._delete_document(collection_type, name)

    def _delete_document(self, collection_type: str, name: str) -> bool:
        if not self._is_connected:
            logger.error("MongoDB manager not connected")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            coll = self.conn_helper.get_collection(collection_type)
            result = coll.delete_one({self.conn_helper.cst_name_field: name})

            if result.deleted_count > 0:
                logger.debug(
                    f"{collection_type.title()} '{safe_name_log(name)}' deleted from MongoDB"
                )
                return True
            else:
                logger.warning(
                    f"{collection_type.title()} '{safe_name_log(name)}' not found for deletion"
                )
                return False
        except (ValidationError, PyMongoError) as e:
            logger.error(
                f"Error deleting {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error deleting {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False

    def exists_federation(self, name: str) -> bool:
        return self.exists("federations", name)

    def exists_scenario(self, name: str) -> bool:
        return self.exists("scenarios", name)

    def exists(self, collection_type: str, name: str) -> bool:
        if not self._is_connected:
            return False
        coll = self.conn_helper.get_collection(collection_type)
        return coll.count_documents({self.conn_helper.cst_name_field: name}) > 0

    def get_database_stats(self) -> Dict[str, Any]:
        if not self._is_connected or not self.conn_helper.db:
            logger.error("MongoDB manager not connected")
            return {}
        try:
            return self.conn_helper.db.command("dbstats")
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
