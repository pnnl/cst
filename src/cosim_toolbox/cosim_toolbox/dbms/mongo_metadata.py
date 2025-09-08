"""
MongoDB-based metadata management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.
"""

import logging
from typing import Any, Dict, Optional, List
import re

try:
    from pymongo import MongoClient
    from pymongo.database import Database
    from pymongo.collection import Collection, UpdateResult, InsertOneResult
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from .abstractions import MDDataWriter, MDDataReader, MDDataManager
from .validation import validate_name, ValidationError, safe_name_log

logger = logging.getLogger(__name__)


class _MongoConnectionHelper:
    """Manages the connection state and logic for MongoDB."""

    def __init__(
        self,
        location: str,
        database: str,
        port: Optional[int] = None,  # Port can still be an override
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )

        # Regex to parse a MongoDB connection string.
        # It captures: 1:protocol, 2:user, 3:password, 4:host(s), 5:port, 6:database
        uri_pattern = re.compile(
            r"^(mongodb(?:\+srv)?):\/\/(?:([^:]+):([^@]+)@)?([^:\/?]+)(?::(\d+))?(?:\/([^\?]+))?"
        )

        match = uri_pattern.match(location)
        if match:
            # The location string is a full or partial URI
            protocol, uri_user, uri_pass, uri_host, uri_port, uri_db = match.groups()
            # Arguments passed to the function override what's in the URI string
            final_user = user or uri_user
            final_pass = password if password is not None else uri_pass
            final_host = uri_host
            final_port = port or (int(uri_port) if uri_port else None)

        else:
            # The location string is just a hostname
            protocol = "mongodb"
            final_host = location
            final_user = user
            final_pass = password
            final_port = port

        # Assemble the final URI string
        auth_part = ""
        if final_user and final_pass is not None:
            from urllib.parse import quote_plus

            auth_part = f"{quote_plus(final_user)}:{quote_plus(final_pass)}@"

        port_part = f":{final_port}" if final_port else ""
        
        self.uri = f"{protocol}://{auth_part}{final_host}{port_part}"
        self.db_name = database

        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.cst_name_field = "cst_007"

    def connect(self) -> bool:
        """Establishes connection to the MongoDB server.
        
        Returns:
            bool: Flag indicating success of connection to MongoDB
        """
        if self.client:
            return True  # Already connected
        try:
            validate_name(self.db_name, context="database name")
            self.client = MongoClient(
                self.uri
                + "/?authSource="
                + self.db_name
                + "&authMechanism=SCRAM-SHA-1",
                serverSelectionTimeoutMS=5000,
            )
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
        """Closes the connection to the MongoDB server.
        
        Returns:
            None
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.debug("MongoDB helper disconnected.")

    def get_collection(self, collection_type: str) -> Collection:
        """Gets a collection object from the database.
        
        Args:
            collection_type (str): Name of collection type

        Returns:
            Collection: Collection of the metadata store
        """
        if self.db is None:
            raise PyMongoError("Not connected to database.")
        if collection_type == "federations":
            return self.db.federations
        elif collection_type == "scenarios":
            return self.db.scenarios
        else:
            validate_name(collection_type, context="collection name")
            return self.db[collection_type]


class MongoMetadataWriter(MDDataWriter):
    """MongoDB-based metadata writer."""

    def __init__(
        self,
        *,  # Everything must be keyword
        location: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        db_name: str = "cst",
        helper: Optional[_MongoConnectionHelper] = None,
    ):
        """Initializes the Mongo writer for standalone or managed use."""
        super().__init__()
        self.helper: _MongoConnectionHelper
        if helper:
            self.helper = helper
            self._owns_connection = False
        elif location:
            self.helper = _MongoConnectionHelper(
                location, db_name, port, user, password
            )
            self._owns_connection = True
        else:
            raise ValueError("Must provide either 'helper' or a 'location'.")

    def connect(self) -> bool:
        """Connects to the database, creating the connection if owned.
        
        Returns:
            bool: Flag indicating successful connection to the Mongo database
        """
        if self._owns_connection:
            if not self.helper.connect():
                return False

        # In both cases, verify the connection exists before setting state
        if self.helper.client:
            self._is_connected = True
            return True
        return False

    def disconnect(self) -> None:
        """Disconnects from the database if the connection is owned.
        
        Returns:
            None
        """
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False

    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write federation metadata to MongoDB

        Args:
            name (str): Name of federation
            federation_data (Dict[str, Any]): Federation metadata
            overwrite (bool, optional): Set flag to overwrite any existing 
                metadata. Defaults to False.

        Returns:
            bool: Flag indicating data was successfully added to MongoDB 
                database
        """
        return self.write("federations", name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write scenario metadata to MongoDB

        Args:
            scenario_data:
            name (str): Name of scenario
            overwrite (bool, optional): Set flag to overwrite any existing
                metadata. Defaults to False.

        Returns:
            bool: Flag indicating data was successfully added to MongoDB 
                database
        """
        return self.write("scenarios", name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Writes arbitrary data to MongoDB database

        Args:
            collection_type (str): Name of collection type where data is to
                be written.
            name (str): Name of metadata to write
            data (Dict[str, Any]): Metadata to write
            overwrite (bool, optional): Set to overwrite any exiting metadata
                of the same name in the MongoDB. Defaults to False.

        Raises:
            ValidationError: Data to write is not a dictionary

        Returns:
            bool: Flag indicating data was successfully written to MongoDB.
        """
        if not self.is_connected:
            logger.error("MongoDB writer not connected. Call connect() first.")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            if not isinstance(data, dict):
                raise ValidationError(f"Data must be a dictionary, got {type(data)}")

            coll = self.helper.get_collection(collection_type)
            name_field = self.helper.cst_name_field

            query = {name_field: name}
            existing = coll.find_one(query)

            if existing and not overwrite:
                logger.error(
                    f"{collection_type.title()} '{safe_name_log(name)}' already exists and overwrite=False"
                )
                return False

            document = {**data, name_field: name}
            result: UpdateResult | InsertOneResult
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
        *,  # Everything must be keyword
        location: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        db_name: str = "cst",
        helper: Optional[_MongoConnectionHelper] = None,
    ):
        """Initializes the Mongo reader for standalone or managed use."""
        super().__init__()
        self.helper: _MongoConnectionHelper
        if helper:
            self.helper = helper
            self._owns_connection = False
        elif location:
            self.helper = _MongoConnectionHelper(
                location, db_name, port, user, password
            )
            self._owns_connection = True
        else:
            raise ValueError("Must provide either 'helper' or a 'location'.")

    def connect(self) -> bool:
        """Connect to MongoDB

        Returns:
            bool: Flag indicating database connection has been established
        """
        if self._owns_connection:
            if not self.helper.connect():
                return False
        if self.helper.client:
            self._is_connected = True
            return True
        return False

    def disconnect(self) -> None:
        """Disconnects from MongoDB

        Returns:
            None
        """
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads the specified federation metadata from MongoDB

        Args:
            name (str): Name of federation to read from MongoDB

        Returns:
            Optional[Dict[str, Any]]: Federation metadata
        """
        return self.read("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads the specified scenario metadata from MongoDB

        Args:
            name (str): Name of scenario to read from MongoDB

        Returns:
            Optional[Dict[str, Any]]: Scenario metadata
        """
        return self.read("scenarios", name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """General read from MongoDB

        Args:
            collection_type (str): Name of collection metadata
            name (str): Metadata name

        Returns:
            Optional[Dict[str, Any]]: metadata from MongoDB
        """
        if not self.is_connected:
            logger.error("MongoDB reader not connected. Call connect() first.")
            return None
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            coll = self.helper.get_collection(collection_type)
            name_field = self.helper.cst_name_field

            document = coll.find_one({"cst_007": name})

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
            logger.error(f"Available scenarios: {self.list_scenarios()}")
            return None

    def list_federations(self) -> List[str]:
        """Produces a list of federations stored in the metadata store

        Returns:
            List[str]: list of federations
        """
        return self.list_items("federations")

    def list_scenarios(self) -> List[str]:
        """Produces a list of scenarios stored in the metadata store

        Returns:
            List[str]: list of scenarios
        """
        return self.list_items("scenarios")

    def list_items(self, collection_type: str) -> List[str]:
        """Produces a list of the named data in the collection in the metadata
        store.

        Args:
            collection_type (str): Collection whose contents are being listed

        Returns:
            List[str]: List of the named data in the specified collection
        """
        if not self.is_connected:
            logger.error("MongoDB reader not connected.")
            return []
        try:
            coll = self.helper.get_collection(collection_type)
            name_field = self.helper.cst_name_field

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
        """Lists custom collection names in metadata store

        Returns:
            List[str]: List of collection names in metadata store
        """
        if not self.is_connected or not self.helper.db:
            logger.error("MongoDB reader not connected.")
            return []
        try:
            all_collections = self.helper.db.list_collection_names()
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
    """Joint MongoDB metadata manager using composition."""

    def __init__(
        self,
        *,  # Everything must be keyword
        location: str,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "cst",
    ):
        super().__init__()
        # The manager creates ONE helper and shares it.
        self.helper: _MongoConnectionHelper = _MongoConnectionHelper(
            location, database, port, user, password
        )
        self.writer: MongoMetadataWriter = MongoMetadataWriter(helper=self.helper)
        self.reader: MongoMetadataReader = MongoMetadataReader(helper=self.helper)

    def connect(self) -> bool:
        """Establish connection for both reader and writer to MongoDB.
        
        Returns:
            bool: Flag indicating that writer and reader are connected
        """
        if not self.helper.connect():
            return False

        # Connect the children (which will just set their internal state)
        self.writer.connect()
        self.reader.connect()
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        """Close connection for both reader and writer to MongoDB.
        
        Returns:
            None
        """
        self.helper.disconnect()
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def delete_federation(self, name: str) -> bool:
        """Deletes the indicated federation metadata from MongoDB

        Args:
            name (str): Name of federation to delete

        Returns:
            bool: Indicates whether the federation metadata has been deleted
        """
        return self._delete_document("federations", name)

    def delete_scenario(self, name: str) -> bool:
        """Deletes the indicated scenario metadata from MongoDB

        Args:
            name (str): Name of scenario to delete

        Returns:
            bool: Indicates whether the scenario metadata has been deleted
        """
        return self._delete_document("scenarios", name)

    def delete(self, collection_type: str, name: str) -> bool:
        """Deletes the specified metadata

        Args:
            collection_type (str): Name of the collection type
            name (str): Name of metadata to delete

        Returns:
            bool: Flag indicating the data has been deleted.
        """
        return self._delete_document(collection_type, name)

    def _delete_document(self, collection_type: str, name: str) -> bool:
        """Delete MongoDB document (dictionary) with proper error handling.

        Args:
            collection_type (str): Name of the collection type
            name (str): Name of metadata to delete

        Returns:
            bool: Flag indicating the data has been deleted.
        """
        if not self._is_connected:
            logger.error("MongoDB manager not connected")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            coll = self.helper.get_collection(collection_type)
            result = coll.delete_one({self.helper.cst_name_field: name})

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
        """Checks to see if federation metadata exists in metadata store

        Args:
            name (str): Name of federation metadata to check for existence

        Returns:
            bool: Flag indicating whether federation metadata exists in
                metadata store
        """
        return self.exists("federations", name)

    def exists_scenario(self, name: str) -> bool:
        """Checks to see if scenario metadata exists in metadata store

        Args:
            name (str): Name of scenario metadata to check for existence

        Returns:
            bool: Flag indicating whether scenario metadata exists in
                metadata store
        """
        return self.exists("scenarios", name)

    def exists(self, collection_type: str, name: str) -> bool:
        """Checks to see if metadata exists

        Args:
            collection_type (str): Collection type name where metadata
                is being checked for existence.
            name (str): Metadata name whose existence is being checked.

        Returns:
            bool: Flag indicating the existence of the named metadata
        """
        if not self._is_connected:
            return False
        coll = self.helper.get_collection(collection_type)
        return coll.count_documents({self.helper.cst_name_field: name}) > 0

    def get_database_stats(self) -> Dict[str, Any]:
        """Gets MongoDB stats

        Returns:
            dict: MongoDB database statistics
        """
        if not self._is_connected or not self.helper.db:
            logger.error("MongoDB manager not connected")
            return {}
        try:
            return self.helper.db.command("dbstats")
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    @property
    def location(self) -> str:
        return self.reader.helper.uri
    
    @property
    def database(self) -> str:
        return self.reader.helper.db_name