"""
JSON file-based metadata management for CoSim Toolbox.
Refactored to use composition-based approach with separate reader/writer classes.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .data_management import (
    MDDataWriter,
    MDDataReader,
    MDDataManager,
    ConnectionInfo,
)

logger = logging.getLogger(__name__)


class JSONMetadataWriter(MDDataWriter):
    """
    JSON file-based metadata writer.
    Writes metadata as JSON files in a structured folder hierarchy.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize JSON metadata writer.
        Args:
            connection_info: Dict containing 'base_path', 'federations_path', 'scenarios_path'
        """
        super().__init__(connection_info)
        self.base_path = connection_info["base_path"]
        self.federations_path = connection_info["federations_path"]
        self.scenarios_path = connection_info["scenarios_path"]

    def _validate_name(self, name: str) -> None:
        """Validate that a name is safe for filesystem use."""
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

    def _get_file_path(self, collection_type: str, name: str) -> Path:
        """Get file path for a given collection type and name."""
        if collection_type == "federations":
            return self.federations_path / f"{name}.json"
        elif collection_type == "scenarios":
            return self.scenarios_path / f"{name}.json"
        else:
            # Custom collection
            collection_path = self.base_path / collection_type
            collection_path.mkdir(exist_ok=True)
            return collection_path / f"{name}.json"

    def connect(self) -> bool:
        """Create directory structure if it doesn't exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.federations_path.mkdir(exist_ok=True)
            self.scenarios_path.mkdir(exist_ok=True)
            self._is_connected = True
            logger.info(f"JSON metadata writer connected to: {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect JSON writer: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files)."""
        self._is_connected = False
        logger.debug("JSON metadata writer disconnected")

    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write federation metadata to JSON file."""
        return self.write("federations", name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write scenario metadata to JSON file."""
        return self.write("scenarios", name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Write metadata to JSON file.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
            data (Dict[str, Any]): Data to write
            overwrite (bool): Whether to overwrite existing data
        Returns:
            bool: True if write successful, False otherwise
        """
        if not self._is_connected:
            logger.error("JSON metadata writer not connected")
            return False

        try:
            self._validate_name(name)

            file_path = self._get_file_path(collection_type, name)

            if file_path.exists() and not overwrite:
                logger.error(
                    f"{collection_type.title()} '{name}' already exists and overwrite=False"
                )
                return False

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"{collection_type.title()} '{name}' written to {file_path}")
            return True

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


class JSONMetadataReader(MDDataReader):
    """
    JSON file-based metadata reader.
    Reads metadata from JSON files in structured folder hierarchy.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize JSON metadata reader.
        Args:
            connection_info: Dict containing 'base_path', 'federations_path', 'scenarios_path'
        """
        super().__init__(connection_info)
        self.base_path = connection_info["base_path"]
        self.federations_path = connection_info["federations_path"]
        self.scenarios_path = connection_info["scenarios_path"]

    def _validate_name(self, name: str) -> None:
        """Validate that a name is safe for filesystem use."""
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

    def _get_file_path(self, collection_type: str, name: str) -> Path:
        """Get file path for a given collection type and name."""
        if collection_type == "federations":
            return self.federations_path / f"{name}.json"
        elif collection_type == "scenarios":
            return self.scenarios_path / f"{name}.json"
        else:
            # Custom collection
            collection_path = self.base_path / collection_type
            return collection_path / f"{name}.json"

    def connect(self) -> bool:
        """Verify that the directory structure exists."""
        try:
            if not self.base_path.exists():
                logger.warning(f"Base path does not exist: {self.base_path}")
                # Don't fail - directory might be created later by writer

            self._is_connected = True
            logger.info(f"JSON metadata reader connected to: {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect JSON reader: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files)."""
        self._is_connected = False
        logger.debug("JSON metadata reader disconnected")

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Read federation metadata from JSON file."""
        return self.read("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Read scenario metadata from JSON file."""
        return self.read("scenarios", name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from JSON file.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
        Returns:
            Optional[Dict[str, Any]]: Data or None if not found
        """
        if not self._is_connected:
            logger.error("JSON metadata reader not connected")
            return None

        try:
            self._validate_name(name)

            file_path = self._get_file_path(collection_type, name)

            if not file_path.exists():
                logger.warning(f"{collection_type.title()} file not found: {file_path}")
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.debug(f"{collection_type.title()} '{name}' read from {file_path}")
            return data

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
            logger.error("JSON metadata reader not connected")
            return []

        try:
            if collection_type == "federations":
                path = self.federations_path
            elif collection_type == "scenarios":
                path = self.scenarios_path
            else:
                path = self.base_path / collection_type

            if not path.exists():
                return []

            return sorted([file_path.stem for file_path in path.glob("*.json")])

        except Exception as e:
            logger.error(f"Failed to list {collection_type}: {e}")
            return []

    def list_custom_collections(self) -> list[str]:
        """List available custom collection names."""
        try:
            return sorted(
                [
                    p.name
                    for p in self.base_path.iterdir()
                    if p.is_dir() and p.name not in ["federations", "scenarios"]
                ]
            )
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


class JSONMetadataManager(MDDataManager):
    """
    Joint JSON metadata manager using composition.
    Combines separate reader and writer instances that share connection information.
    """

    def __init__(self, location: str):
        """
        Initialize JSON metadata manager.
        Args:
            location (str): Base directory path for JSON file storage
        """
        super().__init__(location)

    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create shared connection info for JSON storage."""
        base_path = Path(location)
        federations_path = base_path / "federations"
        scenarios_path = base_path / "scenarios"

        return {
            "base_path": base_path,
            "federations_path": federations_path,
            "scenarios_path": scenarios_path,
        }

    def _create_writer(self, connection_info: ConnectionInfo) -> MDDataWriter:
        """Create JSON writer with shared connection info."""
        return JSONMetadataWriter(connection_info)

    def _create_reader(self, connection_info: ConnectionInfo) -> MDDataReader:
        """Create JSON reader with shared connection info."""
        return JSONMetadataReader(connection_info)

    def delete_federation(self, name: str) -> bool:
        """Delete a federation JSON file."""
        return self._delete_file("federations", name)

    def delete_scenario(self, name: str) -> bool:
        """Delete a scenario JSON file."""
        return self._delete_file("scenarios", name)

    def delete(self, collection_type: str, name: str) -> bool:
        """Delete a JSON file from any collection."""
        return self._delete_file(collection_type, name)

    def _delete_file(self, collection_type: str, name: str) -> bool:
        """
        Delete JSON file.
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Use writer's validation and path logic
            self.writer._validate_name(name)
            file_path = self.writer._get_file_path(collection_type, name)

            if file_path.exists():
                file_path.unlink()
                logger.debug(f"{collection_type.title()} '{name}' deleted")
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
    def base_path(self) -> Path:
        """Get the base path for JSON storage."""
        return self.connection_info["base_path"]

    @property
    def federations_path(self) -> Path:
        """Get the federations directory path."""
        return self.connection_info["federations_path"]

    @property
    def scenarios_path(self) -> Path:
        """Get the scenarios directory path."""
        return self.connection_info["scenarios_path"]