"""
Base metadata manager with common functionality.
"""

import re
from abc import abstractmethod
from typing import Any, Dict, Optional

from .data_management import MDDataWriter, MDDataReader


class BaseMetadataManager(MDDataWriter, MDDataReader):
    """Base class with common metadata management functionality."""

    def __init__(self, location: str):
        super().__init__(location)
        self._is_connected = False

    def _validate_name(self, name: str) -> None:
        """Common name validation logic."""
        if not name or len(name) > 255:
            raise ValueError(f"Name invalid (empty or >255 chars): {name}")

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

    # Abstract methods that each implementation must provide
    @abstractmethod
    def _write_data(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Backend-specific write implementation."""
        pass

    @abstractmethod
    def _read_data(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Backend-specific read implementation."""
        pass

    @abstractmethod
    def _delete_data(self, collection_type: str, name: str) -> bool:
        """Backend-specific delete implementation."""
        pass

    @abstractmethod
    def _list_data(self, collection_type: str) -> list[str]:
        """Backend-specific list implementation."""
        pass

    @abstractmethod
    def _list_collections(self) -> list[str]:
        """Backend-specific method to list available custom collections."""
        pass

    # Context manager methods (still abstract since connection logic varies)
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the storage backend."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    # Common public API using the abstract methods

    # Generic write method
    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Generic write method for any collection type.

        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
            data (Dict[str, Any]): Data to write
            overwrite (bool): Whether to overwrite existing data

        Returns:
            bool: True if write successful, False otherwise
        """
        return self._write_data(collection_type, name, data, overwrite)

    # Convenience methods for standard collections
    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write federation metadata."""
        return self._write_data("federations", name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write scenario metadata."""
        return self._write_data("scenarios", name, scenario_data, overwrite)

    # Generic read method
    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Generic read method for any collection type.

        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name

        Returns:
            Optional[Dict[str, Any]]: Data or None if not found
        """
        return self._read_data(collection_type, name)

    # Convenience methods for standard collections
    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Read federation metadata."""
        return self._read_data("federations", name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Read scenario metadata."""
        return self._read_data("scenarios", name)

    # Generic delete method
    def delete(self, collection_type: str, name: str) -> bool:
        """
        Generic delete method for any collection type.

        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name

        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._delete_data(collection_type, name)

    # Convenience methods for standard collections
    def delete_federation(self, name: str) -> bool:
        """Delete a federation."""
        return self._delete_data("federations", name)

    def delete_scenario(self, name: str) -> bool:
        """Delete a scenario."""
        return self._delete_data("scenarios", name)

    # Generic list method
    def list_items(self, collection_type: str) -> list[str]:
        """
        Generic list method for any collection type.

        Args:
            collection_type (str): Collection/category name

        Returns:
            list[str]: List of item names
        """
        return self._list_data(collection_type)

    # Convenience methods for standard collections
    def list_federations(self) -> list[str]:
        """List available federation names."""
        return self._list_data("federations")

    def list_scenarios(self) -> list[str]:
        """List available scenario names."""
        return self._list_data("scenarios")

    def list_custom_collections(self) -> list[str]:
        """List available custom collection names."""
        return self._list_collections()

    # Generic existence check
    def exists(self, collection_type: str, name: str) -> bool:
        """
        Generic existence check for any collection type.

        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name

        Returns:
            bool: True if item exists, False otherwise
        """
        return name in self.list_items(collection_type)

    # Convenience methods for standard collections
    def exists_federation(self, name: str) -> bool:
        """Check if a federation exists."""
        return self.exists("federations", name)

    def exists_scenario(self, name: str) -> bool:
        """Check if a scenario exists."""
        return self.exists("scenarios", name)

    @property
    def is_connected(self) -> bool:
        """Check if the manager is connected."""
        return self._is_connected
