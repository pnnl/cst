"""
JSON file-based metadata management for CoSim Toolbox.
Refactored to use Composition over Inheritance for clarity and maintainability.

@author Nathan Gray
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, cast

from .abstractions import MDDataWriter, MDDataReader, MDDataManager
from .validation import validate_name, ValidationError, safe_name_log

logger = logging.getLogger(__name__)


class _JSONPathHelper:
    """Manages file path logic for JSON metadata storage."""

    def __init__(self, location: Union[str, Path]):
        self.location = Path(location)
        self.federations_path = self.location / "federations"
        self.scenarios_path = self.location / "scenarios"

    def get_file_path(self, collection_type: str, name: str) -> Path:
        """Get file path for a given collection type and name.
        
        Args:
            collection_type (str): Type of data to store. Standard values are
                "federations" and "scenarios" but could also be custom values
                of an arbitrary types (e.g. "configurations")
            name (str): Name of data to store

        Returns:
            Path: Path to new JSON outputs
        """
        if collection_type == "federations":
            return self.federations_path / f"{name}.json"
        elif collection_type == "scenarios":
            return self.scenarios_path / f"{name}.json"
        else:
            return self.location / collection_type / f"{name}.json"


class JSONMetadataWriter(MDDataWriter):
    """JSON file-based metadata writer."""

    def __init__(
        self,
        *,
        location: Optional[Union[str, Path]] = None,
        helper: Optional[_JSONPathHelper] = None,
    ):
        """
        Initialize the JSON writer.

        For standalone use:
            writer = JSONMetadataWriter(location="/path/to/data")
        For managed use (by JSONMetadataManager):
            helper = _JSONPathHelper(...)
            writer = JSONMetadataWriter(helper=helper)
        """
        super().__init__()
        if not (location or helper):
            raise ValueError("Either 'location' or 'helper' must be provided.")
        location = cast(Union[str, Path], location)
        self.helper: _JSONPathHelper
        self.helper = helper or _JSONPathHelper(location)

    def connect(self) -> bool:
        """Create directory structure if it doesn't exist.
        
        Returns:
            bool: Flag indicating success in creating the necessary
                folders for storing the JSON files.
        """
        try:
            self.helper.location.mkdir(parents=True, exist_ok=True)
            self.helper.federations_path.mkdir(exist_ok=True)
            self.helper.scenarios_path.mkdir(exist_ok=True)
            self._is_connected = True
            logger.info(f"JSON metadata writer connected to: {self.helper.location}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect JSON writer: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files, but maintains state).
        
        Returns:
            None
        """
        self._is_connected = False
        logger.debug("JSON metadata writer disconnected")

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
        """_summary_

        Args:
            collection_type (str): Type of data to store. Standard values are
                "federations" and "scenarios" but could also be custom values
                of an arbitrary types (e.g. "configurations")
            name (str): Name of data to store
            data (Dict[str, Any]): Data to be written
            overwrite (bool, optional): Flag indicating if existing data
                should be overwritten. Defaults to False.

        Returns:
            bool: Flag indicating whether the data was written successfully.
        """
        if not self.is_connected:
            logger.error("JSON metadata writer not connected. Call connect() first.")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            validate_name(collection_type, context="collection type")

            file_path = self.helper.get_file_path(collection_type, name)

            if file_path.exists() and not overwrite:
                logger.error(
                    f"{collection_type.title()} '{safe_name_log(name)}' already exists and overwrite=False"
                )
                return False

            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            logger.debug(
                f"{collection_type.title()} '{safe_name_log(name)}' written to {file_path}"
            )
            return True
        except ValidationError as e:
            logger.error(
                f"Validation error for {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except (OSError, IOError) as e:
            logger.error(
                f"File I/O error writing {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except (TypeError, ValueError) as e:
            logger.error(
                f"JSON serialization error for {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error writing {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False


class JSONMetadataReader(MDDataReader):
    """JSON file-based metadata reader."""

    def __init__(
        self,
        *,
        location: Optional[Union[str, Path]] = None,
        helper: Optional[_JSONPathHelper] = None,
    ):
        """
        Initialize the JSON reader.

        For standalone use:
            reader = JSONMetadataReader(location="/path/to/data")
        For managed use (by JSONMetadataManager):
            helper = _JSONPathHelper(...)
            reader = JSONMetadataReader(helper=helper)
        """
        super().__init__()
        if not (location or helper):
            raise ValueError("Either 'location' or 'helper' must be provided.")
        location = cast(Union[str, Path], location)
        self.helper: _JSONPathHelper
        if helper is None:
            helper = _JSONPathHelper(location)
        self.helper = helper

    def connect(self) -> bool:
        """Verify that the directory structure exists.
        
        Returns:
            bool: Flag indicating whether the JSON files able to be
                accessed or not.
        """
        try:
            if not self.helper.location.exists():
                logger.warning(f"Base path does not exist: {self.helper.location}")
            self._is_connected = True
            logger.info(f"JSON metadata reader connected to: {self.helper.location}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect JSON reader: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files, but maintains state).
        
        Returns:
            None
        """
        self._is_connected = False
        logger.debug("JSON metadata reader disconnected")

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads federation configuration data

        Args:
            name (str): name of federation being read

        Returns:
            Optional[Dict[str, Any]]: Federation configuration data
        """
        return self.read("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads scenario metadata

        Args:
            name (str): name of scenario being read

        Returns:
            Optional[Dict[str, Any]]: Scenario metadata
        """
        return self.read("scenarios", name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Reads data from metadata store, generally data in custom 
        collections.

        Args:
            collection_type (str): name of collection type
            name (str): name of data to be read

        Returns:
            Optional[Dict[str, Any]]: read data
        """
        if not self.is_connected:
            logger.error("JSON metadata reader not connected. Call connect() first.")
            return None
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            validate_name(collection_type, context="collection type")

            file_path = self.helper.get_file_path(collection_type, name)

            if not file_path.exists():
                logger.debug(f"{collection_type.title()} file not found: {file_path}")
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.debug(
                f"{collection_type.title()} '{safe_name_log(name)}' read from {file_path}"
            )
            return data
        except ValidationError as e:
            logger.error(
                f"Validation error for {collection_type} '{safe_name_log(name)}': {e}"
            )
            return None
        except (OSError, IOError) as e:
            logger.error(
                f"File I/O error reading {collection_type} '{safe_name_log(name)}': {e}"
            )
            return None
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON decode error for {collection_type} '{safe_name_log(name)}': {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error reading {collection_type} '{safe_name_log(name)}': {e}"
            )
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
            logger.error("JSON metadata reader not connected.")
            return []
        try:
            if collection_type == "federations":
                path = self.helper.federations_path
            elif collection_type == "scenarios":
                path = self.helper.scenarios_path
            else:
                path = self.helper.location / collection_type

            if not path.exists():
                logger.debug(f"Collection path does not exist: {path}")
                return []

            items = [
                file_path.stem
                for file_path in path.glob("*.json")
                if self._is_valid_item_name(file_path)
            ]
            return sorted(items)
        except Exception as e:
            logger.error(f"Failed to list {collection_type}: {e}")
            return []

    def _is_valid_item_name(self, file_path: Path) -> bool:
        """Checks to see if the provided name has data in the metadata store.

        Args:
            file_path (Path): Path to metadata stores

        Returns:
            bool: Flag indicating whether data exists.
        """
        try:
            validate_name(file_path.stem, context="item name")
            return True
        except ValidationError:
            logger.warning(f"Skipping invalid file name: {file_path.name}")
            return False

    def list_custom_collections(self) -> List[str]:
        """Lists custom collection names in metadata store

        Returns:
            List[str]: List of collection names in metadata store
        """
        if not self.is_connected:
            logger.error("JSON metadata reader not connected.")
            return []
        try:
            if not self.helper.location.exists():
                return []

            collections = [
                path.name
                for path in self.helper.location.iterdir()
                if path.is_dir()
                and path.name not in ["federations", "scenarios"]
                and self._is_valid_collection_name(path)
            ]
            return sorted(collections)
        except Exception as e:
            logger.error(f"Failed to list custom collections: {e}")
            return []

    def _is_valid_collection_name(self, path: Path) -> bool:
        """Checks to see if the provided path is for a valid collection name

        Args:
            path (Path): Path to metadata collection

        Returns:
            bool: Flag indicating whether the metadata collection is valid
        """
        try:
            validate_name(path.name, context="collection name")
            return True
        except ValidationError:
            logger.warning(f"Skipping invalid collection name: {path.name}")
            return False


class JSONMetadataManager(MDDataManager):
    """
    Joint JSON metadata manager using composition.
    Manages a shared Path Helper for a single reader and writer instance.
    """

    def __init__(self, location: str):
        """
        Initialize JSON metadata manager.
        Args:
            location (str): Base path for data storage.
        """
        super().__init__()
        # The manager creates ONE helper and shares it with the reader/writer.
        self.helper: _JSONPathHelper = _JSONPathHelper(location)
        self.writer: JSONMetadataWriter = JSONMetadataWriter(helper=self.helper)
        self.reader: JSONMetadataReader = JSONMetadataReader(helper=self.helper)

    def connect(self) -> bool:
        """Establish connection for both reader and writer.
        
        Returns:
            bool: Flag indicating that writer and reader are connected
        """
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Close connection for both reader and writer.
        
        Returns:
            None
        """
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def delete_federation(self, name: str) -> bool:
        """Deletes the indicated federation metadata from the metadata store

        Args:
            name (str): Name of federation to delete

        Returns:
            bool: Indicates whether the federation metadata has been deleted
        """
        return self._delete_file("federations", name)

    def delete_scenario(self, name: str) -> bool:
        """Deletes the indicated scenario metadata from the metadata store

        Args:
            name (str): Name of scenario to delete

        Returns:
            bool: Indicates whether the scenario metadata has been deleted
        """
        return self._delete_file("scenarios", name)

    def delete(self, collection_type: str, name: str) -> bool:
        """Deletes the specified metadata

        Args:
            collection_type (str): Name of the collection type
            name (str): Name of metadata to delete

        Returns:
            bool: Flag indicating the data has been deleted.
        """
        return self._delete_file(collection_type, name)

    def _delete_file(self, collection_type: str, name: str) -> bool:
        """Delete JSON file with proper error handling.

        Args:
            collection_type (str): Name of the collection type
            name (str): Name of metadata to delete

        Returns:
            bool: Flag indicating the data has been deleted.
        """
        if not self._is_connected:
            logger.error("JSON metadata manager not connected")
            return False
        try:
            validate_name(name, context=f"{collection_type.rstrip('s')}")
            validate_name(collection_type, context="collection type")

            file_path = self.reader.helper.get_file_path(collection_type, name)
            if file_path.exists():
                file_path.unlink()
                logger.debug(
                    f"{collection_type.title()} '{safe_name_log(name)}' deleted"
                )
                return True
            else:
                logger.warning(
                    f"{collection_type.title()} '{safe_name_log(name)}' not found for deletion"
                )
                return False
        except ValidationError as e:
            logger.error(
                f"Validation error for {collection_type} '{safe_name_log(name)}': {e}"
            )
            return False
        except (OSError, IOError) as e:
            logger.error(
                f"File I/O error deleting {collection_type} '{safe_name_log(name)}': {e}"
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
        return self.reader.helper.get_file_path("federations", name).exists()

    def exists_scenario(self, name: str) -> bool:
        """Checks to see if scenario metadata exists in metadata store

        Args:
            name (str): Name of scenario metadata to check for existence

        Returns:
            bool: Flag indicating whether scenario metadata exists in
                metadata store
        """
        return self.reader.helper.get_file_path("scenarios", name).exists()

    def exists(self, collection_type: str, name: str) -> bool:
        """Checks to see if metadata exists

        Args:
            collection_type (str): Collection type name where metadata
                is being checked for existence.
            name (str): Metadata name whose existence is being checked.

        Returns:
            bool: Flag indicating the existence of the named metadata
        """
        return self.reader.helper.get_file_path(collection_type, name).exists()

    def backup_collection(self, collection_type: str, backup_path: str) -> bool:
        """Backs up the specified collection to the specified location

        Args:
            collection_type (str): Name of collection type
            backup_path (str): Backup location for collection

        Returns:
            bool: Flag indicating the collection has been backed up
        """
        try:
            if collection_type == "federations":
                source_path = self.reader.helper.federations_path
            elif collection_type == "scenarios":
                source_path = self.reader.helper.scenarios_path
            else:
                source_path = self.reader.helper.location / collection_type

            if not source_path.exists():
                logger.warning(
                    f"Collection {collection_type} does not exist, nothing to backup"
                )
                return True

            backup_dest = Path(backup_path)
            backup_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_path, backup_dest, dirs_exist_ok=True)
            logger.info(f"Backed up collection {collection_type} to {backup_dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup collection {collection_type}: {e}")
            return False

    @property
    def location(self) -> Path:
        return self.reader.helper.location

    @property
    def federations_path(self) -> Path:
        return self.reader.helper.federations_path

    @property
    def scenarios_path(self) -> Path:
        return self.reader.helper.scenarios_path
