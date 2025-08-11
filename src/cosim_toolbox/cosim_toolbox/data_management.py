"""
Created on [DATE]
Core data management abstractions for CoSim Toolbox.
Provides TSRecord dataclass and abstract base classes for DataWriter and DataReader.
@author: [AUTHOR]
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Union
import pandas as pd


@dataclass
class TSRecord:
    """
    Time-series record dataclass that holds a single time-series record.
    This dataclass defines the standard structure for time-series data in CST,
    matching the current database schema. Type hints provide IDE support and
    help ensure correct datatypes are used.
    """

    real_time: datetime
    sim_time: float
    scenario: str
    federate: str
    data_name: str
    data_value: Any

    def __post_init__(self):
        """Validate data types if needed (currently disabled for performance)"""
        # Optional validation could be added here
        pass


# Connection info type for sharing between readers and writers
ConnectionInfo = Dict[str, Any]


class TSDataWriter(ABC):
    """
    Abstract base class for time-series data writers.
    All time-series data writers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize the writer with shared connection information.
        Args:
            connection_info: Shared connection details (varies by implementation)
        """
        self.connection_info = connection_info
        self._buffer = []
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data store using shared connection info.
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the data store.
        """
        pass

    @abstractmethod
    def write_records(self, records: list[TSRecord]) -> bool:
        """
        Write TSRecord objects to the data store.
        Args:
            records (list[TSRecord]): List of time-series records to write
        Returns:
            bool: True if write successful, False otherwise
        """
        pass

    def add_record(self, record: TSRecord) -> None:
        """
        Add a single TSRecord to the internal buffer.
        Args:
            record (TSRecord): Time-series record to add
        """
        self._buffer.append(record)

    def flush(self) -> bool:
        """
        Write all buffered records to the data store and clear buffer.
        Returns:
            bool: True if flush successful, False otherwise
        """
        if self._buffer:
            success = self.write_records(self._buffer)
            if success:
                self._buffer.clear()
            return success
        return True

    @property
    def buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)

    @property
    def is_connected(self) -> bool:
        """Check if the writer is connected."""
        return self._is_connected


class TSDataReader(ABC):
    """
    Abstract base class for time-series data readers.
    All time-series data readers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize the reader with shared connection information.
        Args:
            connection_info: Shared connection details (varies by implementation)
        """
        self.connection_info = connection_info
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data store using shared connection info.
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the data store.
        """
        pass

    @abstractmethod
    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read time-series data from the data store.
        Args:
            start_time (Optional[float]): Starting time for data query
            duration (Optional[float]): Duration in seconds for data query
            scenario_name (Optional[str]): Filter by scenario name
            federate_name (Optional[str]): Filter by federate name
            data_name (Optional[str]): Filter by data name
        Returns:
            pd.DataFrame: Time-series data as a Pandas DataFrame
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the reader is connected."""
        return self._is_connected


class MDDataWriter(ABC):
    """
    Abstract base class for metadata writers.
    All metadata writers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize the writer with shared connection information.
        Args:
            connection_info: Shared connection details (varies by implementation)
        """
        self.connection_info = connection_info
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data store using shared connection info.
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the data store.
        """
        pass

    @abstractmethod
    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """
        Write federation metadata to the data store.
        Args:
            name (str): Federation name
            federation_data (Dict[str, Any]): Federation configuration data
            overwrite (bool): Whether to overwrite existing data
        Returns:
            bool: True if write successful, False otherwise
        """
        pass

    @abstractmethod
    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """
        Write scenario metadata to the data store.
        Args:
            name (str): Scenario name
            scenario_data (Dict[str, Any]): Scenario configuration data
            overwrite (bool): Whether to overwrite existing data
        Returns:
            bool: True if write successful, False otherwise
        """
        pass

    @abstractmethod
    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """
        Write metadata to the data store (generic method).
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
            data (Dict[str, Any]): Data to write
            overwrite (bool): Whether to overwrite existing data
        Returns:
            bool: True if write successful, False otherwise
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the writer is connected."""
        return self._is_connected


class MDDataReader(ABC):
    """
    Abstract base class for metadata readers.
    All metadata readers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize the reader with shared connection information.
        Args:
            connection_info: Shared connection details (varies by implementation)
        """
        self.connection_info = connection_info
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data store using shared connection info.
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the data store.
        """
        pass

    @abstractmethod
    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Read federation metadata from the data store.
        Args:
            name (str): Federation name
        Returns:
            Optional[Dict[str, Any]]: Federation data or None if not found
        """
        pass

    @abstractmethod
    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Read scenario metadata from the data store.
        Args:
            name (str): Scenario name
        Returns:
            Optional[Dict[str, Any]]: Scenario data or None if not found
        """
        pass

    @abstractmethod
    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from the data store (generic method).
        Args:
            collection_type (str): Collection/category name
            name (str): Data identifier name
        Returns:
            Optional[Dict[str, Any]]: Data or None if not found
        """
        pass

    @abstractmethod
    def list_federations(self) -> list[str]:
        """
        List available federation names.
        Returns:
            list[str]: List of federation names
        """
        pass

    @abstractmethod
    def list_scenarios(self) -> list[str]:
        """
        List available scenario names.
        Returns:
            list[str]: List of scenario names
        """
        pass

    @abstractmethod
    def list_items(self, collection_type: str) -> list[str]:
        """
        List available items in a collection (generic method).
        Args:
            collection_type (str): Collection/category name
        Returns:
            list[str]: List of item names
        """
        pass

    @abstractmethod
    def list_custom_collections(self) -> list[str]:
        """
        List available custom collection names.
        Returns:
            list[str]: List of custom collection names
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the reader is connected."""
        return self._is_connected


# Joint Manager Classes (composition-based)
class TSDataManager(ABC):
    """
    Abstract base class for combined time-series data management.
    This class uses composition to combine separate reader and writer instances
    that share a common connection.
    """

    def __init__(self, location: str, **kwargs):
        """
        Initialize the time-series data manager.
        Args:
            location (str): Storage location specification
            **kwargs: Backend-specific parameters
        """
        self.location = location
        self._is_connected = False
        self.connection_info = self._create_connection_info(location, **kwargs)

        # Create reader and writer instances with shared connection info
        self.writer = self._create_writer(self.connection_info)
        self.reader = self._create_reader(self.connection_info)

    @abstractmethod
    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create connection info to be shared between reader and writer."""
        pass

    @abstractmethod
    def _create_writer(self, connection_info: ConnectionInfo) -> TSDataWriter:
        """Create writer instance with shared connection info."""
        pass

    @abstractmethod
    def _create_reader(self, connection_info: ConnectionInfo) -> TSDataReader:
        """Create reader instance with shared connection info."""
        pass

    def connect(self) -> bool:
        """Establish connection for both reader and writer."""
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Close connection for both reader and writer."""
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    # Delegate methods to composed instances
    def write_records(self, records: list[TSRecord]) -> bool:
        """Write time-series records to the data store."""
        return self.writer.write_records(records)

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read time-series data from the data store."""
        return self.reader.read_data(
            start_time=start_time,
            duration=duration,
            scenario_name=scenario_name,
            federate_name=federate_name,
            data_name=data_name,
            data_type=data_type,
        )

    def add_record(self, record: TSRecord) -> None:
        """Add a single TSRecord to the writer's internal buffer."""
        self.writer.add_record(record)

    def flush(self) -> bool:
        """Write all buffered records to the data store and clear buffer."""
        return self.writer.flush()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    @property
    def buffer_size(self) -> int:
        """Get current buffer size."""
        return self.writer.buffer_size

    @property
    def is_connected(self) -> bool:
        """Check if the manager is connected."""
        return self._is_connected


class MDDataManager(ABC):
    """
    Abstract base class for combined metadata management.
    This class uses composition to combine separate reader and writer instances
    that share a common connection.
    """

    def __init__(self, location: str, **kwargs):
        """
        Initialize the metadata manager.
        Args:
            location (str): Storage location specification
            **kwargs: Backend-specific parameters
        """
        self.location = location
        self._is_connected = False
        self.connection_info = self._create_connection_info(location, **kwargs)

        # Create reader and writer instances with shared connection info
        self.writer = self._create_writer(self.connection_info)
        self.reader = self._create_reader(self.connection_info)

    @abstractmethod
    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create connection info to be shared between reader and writer."""
        pass

    @abstractmethod
    def _create_writer(self, connection_info: ConnectionInfo) -> MDDataWriter:
        """Create writer instance with shared connection info."""
        pass

    @abstractmethod
    def _create_reader(self, connection_info: ConnectionInfo) -> MDDataReader:
        """Create reader instance with shared connection info."""
        pass

    def connect(self) -> bool:
        """Establish connection for both reader and writer."""
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Close connection for both reader and writer."""
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    # Delegate write methods to writer
    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write federation metadata."""
        return self.writer.write_federation(name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Write scenario metadata."""
        return self.writer.write_scenario(name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Generic write method."""
        return self.writer.write(collection_type, name, data, overwrite)

    # Delegate read methods to reader
    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Read federation metadata."""
        return self.reader.read_federation(name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Read scenario metadata."""
        return self.reader.read_scenario(name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Generic read method."""
        return self.reader.read(collection_type, name)

    def list_federations(self) -> list[str]:
        """List available federation names."""
        return self.reader.list_federations()

    def list_scenarios(self) -> list[str]:
        """List available scenario names."""
        return self.reader.list_scenarios()

    def list_items(self, collection_type: str) -> list[str]:
        """List available items in a collection."""
        return self.reader.list_items(collection_type)

    def list_custom_collections(self) -> list[str]:
        """List available custom collection names."""
        return self.reader.list_custom_collections()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if the manager is connected."""
        return self._is_connected


# Type aliases for convenience
MetadataManager = MDDataManager
TimeSeriesManager = TSDataManager


# Factory function type hint
def create_metadata_manager(backend: str, location: str, **kwargs) -> MetadataManager:
    """
    Factory function to create metadata managers.
    Implementation in metadata_factory.py
    """
    pass


def create_timeseries_manager(
    backend: str, location: str, **kwargs
) -> TimeSeriesManager:
    """
    Factory function to create time-series managers.
    Implementation will be in timeseries_factory.py
    """
    pass
