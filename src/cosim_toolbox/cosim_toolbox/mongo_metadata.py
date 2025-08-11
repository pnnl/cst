"""
MongoDB-based metadata management for CoSim Toolbox.
Refactored to use composition-based approach with separate reader/writer classes.
"""

import logging
from typing import Any, Dict, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from .data_management import (
    MDDataWriter,
    MDDataReader,
    MDDataManager,
    ConnectionInfo,
)

logger = logging.getLogger(__name__)


class MongoMetadataWriter(MDDataWriter):
    """
    MongoDB-based metadata writer.
    Writes metadata as documents in MongoDB collections.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize MongoDB metadata writer.
        Args:
            connection_info: Dict containing 'uri', 'db_name', 'client', 'db'
        """
        super().__init__(connection_info)
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )

        self.uri = connection_info["uri"]
        self.db_name = connection_info["db_name"]
        self._cst_name_field = "cst_name"  # Field name for document identification

    def _validate_name(self, name: str) -> None:
        """Validate that a name is safe for MongoDB use."""
        if not name or len(name) > 255:
            raise ValueError(f"Name invalid (empty or >255 chars): {name}")

        import re
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
            raise ValueError(f"Name contains invalid characters: {name}")

        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{p}{i}" for p in ["COM", "LPT"] for i in range(1, 10)
        }
        if (
            name.upper() in reserved
            or name.startswith((" ", "."))
            or name.endswith((" ", "."))
        ):
            raise ValueError(f"Name is reserved or has invalid format: {name}")

    def _get_collection(self, collection_type: str):
        """Get MongoDB collection object."""
        db = self.connection_info["db"]
        if collection_type == "federations":
            return db.federations
        elif collection_type == "scenarios":
            return db.scenarios
        else:
            # Custom collection
            return db[collection_type]

    def connect(self) -> bool:
        """Connect to MongoDB (shared connection managed by manager)."""
        # Connection is managed by the manager, just verify it exists
        if "client" in self.connection_info and "db" in self.connection_info:
            self._is_connected = True
            logger.info(f"MongoDB metadata writer using shared connection to: {self.uri}/{self.db_name}")
            return True
        else:
            logger.error("MongoDB writer: shared connection not available")
            return False

    def disconnect(self) -> None:
        """Disconnect from MongoDB (managed by manager)."""
        self._is_connected = False
        logger.debug("MongoDB metadata writer disconnected")

    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write federation metadata to MongoDB."""
        return self.write("federations", name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write scenario metadata to MongoDB."""
        return self.write("scenarios", name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Write metadata to MongoDB collection.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
            data (Dict[str, Any]): Data to write
            overwrite (bool): Whether to overwrite existing data
        Returns:
            bool: True if write successful, False otherwise
        """
        if not self._is_connected:
            logger.error("MongoDB metadata writer not connected")
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

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class MongoMetadataReader(MDDataReader):
    """
    MongoDB-based metadata reader.
    Reads metadata from MongoDB collections.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize MongoDB metadata reader.
        Args:
            connection_info: Dict containing 'uri', 'db_name', 'client', 'db'
        """
        super().__init__(connection_info)
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )

        self.uri = connection_info["uri"]
        self.db_name = connection_info["db_name"]
        self._cst_name_field = "cst_name"  # Field name for document identification

    def _validate_name(self, name: str) -> None:
        """Validate that a name is safe for MongoDB use."""
        if not name or len(name) > 255:
            raise ValueError(f"Name invalid (empty or >255 chars): {name}")

        import re
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
            raise ValueError(f"Name contains invalid characters: {name}")

        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{p}{i}" for p in ["COM", "LPT"] for i in range(1, 10)
        }
        if (
            name.upper() in reserved
            or name.startswith((" ", "."))
            or name.endswith((" ", "."))
        ):
            raise ValueError(f"Name is reserved or has invalid format: {name}")

    def _get_collection(self, collection_type: str):
        """Get MongoDB collection object."""
        db = self.connection_info["db"]
        if collection_type == "federations":
            return db.federations
        elif collection_type == "scenarios":
            return db.scenarios
        else:
            # Custom collection
            return db[collection_type]

    def connect(self) -> bool:
        """Connect to MongoDB (shared connection managed by manager)."""
        # Connection is managed by the manager, just verify it exists
        if "client" in self.connection_info and "db" in self.connection_info:
            self._is_connected = True
            logger.info(f"MongoDB metadata reader using shared connection to: {self.uri}/{self.db_name}")
            return True
        else:
            logger.error("MongoDB reader: shared connection not available")
            return False

    def disconnect(self) -> None:
        """Disconnect from MongoDB (managed by manager)."""
        self._is_connected = False
        logger.debug("MongoDB metadata reader disconnected")

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Read federation metadata from MongoDB."""
        return self.read("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Read scenario metadata from MongoDB."""
        return self.read("scenarios", name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from MongoDB collection.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
        Returns:
            Optional[Dict[str, Any]]: Data or None if not found
        """
        if not self._is_connected:
            logger.error("MongoDB metadata reader not connected")
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

    def list_federations(self) -> list[str]:
        """List available federation names."""
        return self.list_items("federations")

    def list_scenarios(self) -> list[str]:
        """List available scenario names."""
        return self.list_items("scenarios")

    def list_items(self, collection_type: str) -> list[str]:
        """
        List available items in a collection.
        Args:
            collection_type (str): Collection/category name
        Returns:
            list[str]: List of item names
        """
        if not self._is_connected:
            logger.error("MongoDB metadata reader not connected")
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

    def list_custom_collections(self) -> list[str]:
        """List available custom collection names."""
        if not self._is_connected:
            logger.error("MongoDB metadata reader not connected")
            return []

        try:
            db = self.connection_info["db"]
            # Get all collection names and filter out standard ones
            all_collections = db.list_collection_names()
            custom_collections = [
                name
                for name in all_collections
                if name not in ["federations", "scenarios"]
            ]
            return sorted(custom_collections)
        except Exception as e:
            logger.error(f"Failed to list custom collections: {e}")
            return []

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class MongoMetadataManager(MDDataManager):
    """
    Joint MongoDB metadata manager using composition.
    Combines separate reader and writer instances that share a common connection.
    """

    def __init__(self, location: str, db_name: str = "cst"):
        """
        Initialize MongoDB metadata manager.
        Args:
            location (str): MongoDB URI
            db_name (str): Database name (default: "cst")
        """
        self.uri = location
        self.db_name = db_name
        self.client = None
        self.db = None
        super().__init__(location, db_name=db_name)

    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create shared connection info for MongoDB storage."""
        db_name = kwargs.get("db_name", "cst")
        
        return {
            "uri": location,
            "db_name": db_name,
            "client": None,  # Will be set when connected
            "db": None,      # Will be set when connected
        }

    def _create_writer(self, connection_info: ConnectionInfo) -> MDDataWriter:
        """Create MongoDB writer with shared connection info."""
        return MongoMetadataWriter(connection_info)

    def _create_reader(self, connection_info: ConnectionInfo) -> MDDataReader:
        """Create MongoDB reader with shared connection info."""
        return MongoMetadataReader(connection_info)

    def connect(self) -> bool:
        """Establish MongoDB connection and share it with reader/writer."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)

            # Test the connection
            self.client.admin.command("ping")

            self.db = self.client[self.db_name]

            # Update shared connection info
            self.connection_info["client"] = self.client
            self.connection_info["db"] = self.db

            # Now connect reader and writer (they'll use the shared connection)
            writer_connected = self.writer.connect()
            reader_connected = self.reader.connect()
            
            self._is_connected = writer_connected and reader_connected

            logger.info(
                f"MongoDB metadata manager connected to: {self.uri}/{self.db_name}"
            )
            return self._is_connected

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from MongoDB and close shared connection."""
        # Disconnect reader and writer first
        self.writer.disconnect()
        self.reader.disconnect()

        # Close the shared connection
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

        # Clear shared connection info
        self.connection_info["client"] = None
        self.connection_info["db"] = None

        self._is_connected = False
        logger.debug("MongoDB metadata manager disconnected")

    def delete_federation(self, name: str) -> bool:
        """Delete a federation document."""
        return self._delete_document("federations", name)

    def delete_scenario(self, name: str) -> bool:
        """Delete a scenario document."""
        return self._delete_document("scenarios", name)

    def delete(self, collection_type: str, name: str) -> bool:
        """Delete a document from any collection."""
        return self._delete_document(collection_type, name)

    def _delete_document(self, collection_type: str, name: str) -> bool:
        """
        Delete document from MongoDB collection.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self._is_connected:
            logger.error("MongoDB metadata manager not connected")
            return False

        try:
            # Use writer's validation logic
            self.writer._validate_name(name)

            coll = self.writer._get_collection(collection_type)
            result = coll.delete_one({self.writer._cst_name_field: name})

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

    def exists_federation(self, name: str) -> bool:
        """Check if a federation exists."""
        return name in self.list_federations()

    def exists_scenario(self, name: str) -> bool:
        """Check if a scenario exists."""
        return name in self.list_scenarios()

    def exists(self, collection_type: str, name: str) -> bool:
        """Check if an item exists in a collection."""
        return name in self.list_items(collection_type)

    @property
    def uri(self) -> str:
        """Get the MongoDB URI."""
        return self.connection_info["uri"]

    @uri.setter
    def uri(self, value: str) -> None:
        """Set the MongoDB URI."""
        self._uri = value
        if hasattr(self, 'connection_info'):
            self.connection_info["uri"] = value

    @property
    def db_name(self) -> str:
        """Get the database name."""
        return self.connection_info["db_name"]

    @db_name.setter
    def db_name(self, value: str) -> None:
        """Set the database name."""
        self._db_name = value
        if hasattr(self, 'connection_info'):
            self.connection_info["db_name"] = value