"""
JSON file-based metadata management for CoSim Toolbox.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .base_metadata import BaseMetadataManager

logger = logging.getLogger(__name__)


class JSONMetadataManager(BaseMetadataManager):
    """JSON file-based metadata manager."""

    def __init__(self, location: str):
        super().__init__(location)
        self.base_path = Path(location)
        self.federations_path = self.base_path / "federations"
        self.scenarios_path = self.base_path / "scenarios"

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

    def _write_data(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Write JSON data to file."""
        if not self._is_connected:
            logger.error("JSON metadata manager not connected")
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

    def _read_data(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from file."""
        if not self._is_connected:
            logger.error("JSON metadata manager not connected")
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

    def _delete_data(self, collection_type: str, name: str) -> bool:
        """Delete JSON file."""
        try:
            self._validate_name(name)

            file_path = self._get_file_path(collection_type, name)

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

    def _list_data(self, collection_type: str) -> list[str]:
        """List JSON files in a collection."""
        if not self._is_connected:
            logger.error("JSON metadata manager not connected")
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

    def _list_collections(self) -> list[str]:
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

    def connect(self) -> bool:
        """Create directory structure if it doesn't exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.federations_path.mkdir(exist_ok=True)
            self.scenarios_path.mkdir(exist_ok=True)
            self._is_connected = True
            logger.info(f"JSON metadata manager connected to: {self.location}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files)."""
        self._is_connected = False
        logger.debug("JSON metadata manager disconnected")
