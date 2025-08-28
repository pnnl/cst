"""
Core data management abstractions for CoSim Toolbox.
Provides TSRecord dataclass and abstract base classes for data I/O.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd


@dataclass
class TSRecord:
    real_time: datetime
    sim_time: float
    scenario: str
    federate: str
    data_name: str
    data_value: Any
    data_type: Optional[str] = None  # "hdt_string", "hdt_endpoint", "hdt_double", etc.

    def __post_init__(self) -> None:
        # Auto-detect type if not provided
        if self.data_type is None:
            self.data_type = self._auto_detect_type()

    def _auto_detect_type(self) -> str:
        """Auto-detect data type from value"""
        if isinstance(self.data_value, bool):
            return "hdt_boolean"
        if isinstance(self.data_value, int):
            return "hdt_integer"
        if isinstance(self.data_value, float):
            return "hdt_double"
        if isinstance(self.data_value, complex):
            return "hdt_complex"
        if isinstance(self.data_value, str):
            return "hdt_string"
        if isinstance(self.data_value, (list, tuple)):
            return "hdt_vector"  # Could be enhanced for complex vectors
        return "hdt_string"  # Default fallback


class TSDataWriter(ABC):
    """
    Abstract base class for time-series data writers.
    All time-series data writers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self) -> None:
        """Initializes the base writer state.
        
        Args: 
            None

        Returns:
            None
        
        """
        self.helper: object
        self._buffer: list = []
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data store.
        
        Args: 
            None

        Returns:
            None

        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data store.
        
        Args: 
            None

        Returns:
            None

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

        Returns:
            None
        """
        self._buffer.append(record)

    def flush(self) -> bool:
        """
        Write all buffered records to the data store and clear buffer.
        
        Args:
            None

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
        """Get current buffer size.
        
        Args: 
            None

        Returns:
            int: number of elements in buffer list
        
        """
        return len(self._buffer)

    @property
    def is_connected(self) -> bool:
        """Check if the writer is connected.
        
        Args: 
            None

        Returns:
            bool: True if writer is connected to data backend
        
        """
        return self._is_connected

    def __enter__(self):
        """Context manager entry.
        
        Args: 
            None

        Returns:
            None
        
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from database.
        
        Args: 
            None

        Returns:
            None
        """
        self.disconnect()


class TSDataReader(ABC):
    """
    Abstract base class for time-series data readers.
    All time-series data readers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self) -> None:
        """Initializes the base reader state."""
        self.helper: object
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data store.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        raise NotImplementedError(
                "TSDataReader.connect() is an abstract class and must be " \
                "subclassed and implemented."
            )

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data store.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        raise NotImplementedError(
                "TSDataReader.disconnect() is an abstract class and must be" \
                "subclassed and implemented."
            )

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
            data_type (Optional[str]): Filter by data type
        Returns:
            pd.DataFrame: Time-series data as a Pandas DataFrame
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the reader is connected.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        return self._is_connected

    def __enter__(self):
        """Context manager entry.
        
        Args: 
            None

        Returns:
            None
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from database."""
        self.disconnect()


class MDDataWriter(ABC):
    """
    Abstract base class for metadata writers.
    All metadata writers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self) -> None:
        """Initializes the base writer state.
        
        Args: 
            None

        Returns:
            None
        """
        self.helper: object
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data store.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend
                was established
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data store.
        Args: 
            None

        Returns:
            None
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
        """Check if the writer is connected.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        return self._is_connected

    def __enter__(self):
        """Context manager entry.
        
        Args: 
            None

        Returns:
            None
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from database.
        
        Args: 
            None

        Returns:
            None
        """
        self.disconnect()


class MDDataReader(ABC):
    """
    Abstract base class for metadata readers.
    All metadata readers must implement these methods to provide
    a consistent API across different storage backends.
    """

    def __init__(self) -> None:
        """Initializes the base reader state.
        
        Args: 
            None

        Returns:
            None
        """
        self.helper: object
        self._is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data store.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        raise NotImplementedError(
                "MDDataReader.connect() is an abstract class and must be" \
                "subclassed and implemented."
            )

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data store.
        
        Args: 
            None

        Returns:
            bool: flag indicated if the connection to the data backend exists
        """
        raise NotImplementedError(
                "MDDataReader.disconnect() is an abstract class and must be" \
                "subclassed and implemented."
            )

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
        """List available federation names.
        
        Args: 
            None

        Returns:
            list[str]: list of names of federations as strings
        """
        pass

    @abstractmethod
    def list_scenarios(self) -> list[str]:
        """List available scenario names.
        
        Args: 
            None

        Returns:
            list[str]: list of names of scenarios as strings
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
        
        Args:
            None

        Returns:
            list[str]: List of custom collection names
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if the reader is connected.
        
        Args: 
            None

        Returns:
            bool: flag indicating if data backend is connected
        """
        return self._is_connected

    def __enter__(self):
        """Context manager entry.
        
        Args: 
            None

        Returns:
            None
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from database.
        
        Args: 
            None

        Returns:
            None
        """
        self.disconnect()


# Joint Manager Classes (composition-based)
class TSDataManager(ABC):
    """
    Abstract base class for combined time-series data management.
    """

    def __init__(self, **kwargs) -> None:
        self._is_connected = False
        self.helper: object
        self.writer: TSDataWriter
        self.reader: TSDataReader

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection for both reader and writer.
        
        Args: 
            None

        Returns:
            bool: flag indicating whether the connection to the backend exist
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection for both reader and writer.
        
        Args: 
            None

        Returns:
            None

        """
        pass

    def write_records(self, records: list[TSRecord]) -> bool:
        """Writes records to the data backend

        Args:
            records (list[TSRecord]): Data to be written to the data backend

        Returns:
            bool: flag indicating whether the data was successfully written
                to the data backend
        """
        return self.writer.write_records(records)

    def read_data(self, **kwargs) -> pd.DataFrame:
        """Reads data from data backedn

        Args:
            None

        Returns:
            pd.DataFrame: Requested data from data backend
        """
        return self.reader.read_data(**kwargs)

    def add_record(self, record: TSRecord) -> None:
        """Adds a single record (data point) to the data backend

        Args:
            record (TSRecord): Data record to be written

        Returns:
            None
        """
        self.writer.add_record(record)

    def flush(self) -> bool:
        """_summary_

        Args:
            None
        
        Returns:
            bool: flag indicating the success of the write to disk
        """
        return self.writer.flush()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @property
    def buffer_size(self) -> int:
        """Gets the number of elements in the data buffer

        Returns:
            int: number of elements in the data buffer
        """
        return self.writer.buffer_size

    @property
    def is_connected(self) -> bool:
        """Flag indicating if connected to the data backend

        Args:
            None

        Returns:
            bool: flag indicating if connected to the data backend
        """
        return self._is_connected


class MDDataManager(ABC):
    """
    Abstract base class for combined metadata management.
    """

    def __init__(self, **kwargs) -> None:
        self._is_connected = False
        self.helper: object
        self.writer: MDDataWriter
        self.reader: MDDataReader

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection for both reader and writer.
        
        Args:
            None

        Returns:
            bool: flag indicating if connected to the data backend
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection for both reader and writer.
        
        Args:
            None

        Returns:
            None
        """
        pass

    def write_federation(
        self, name: str, federation_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Writes passed in federation data to the data backend

        Args:
            name (str): **TODO**
            federation_data (Dict[str, Any]): federation data dictionary to be
                written
            overwrite (bool, optional): Flag indicating if any existing 
                federation dictionary should be overwritten. Defaults to 
                False.

        Returns:
            bool: flag indicating whether the federation dictionary was 
                successfully written to the data backend
        """
        return self.writer.write_federation(name, federation_data, overwrite)

    def write_scenario(
        self, name: str, scenario_data: Dict[str, Any], overwrite: bool = False
    ) -> bool:
        """Writes passed in scenario data to the data backend

        Args:
            name (str): **TODO**
            scenario_data (Dict[str, Any]): scenario data dictionary to be
                written
            overwrite (bool, optional): Flag indicating if any existing 
                scenario dictionary should be overwritten. Defaults to False.

        Returns:
            bool: flag indicating whether the scenario dictionary was 
                successfully written to the data backend
        """
        return self.writer.write_scenario(name, scenario_data, overwrite)

    def write(
        self,
        collection_type: str,
        name: str,
        data: Dict[str, Any],
        overwrite: bool = False,
    ) -> bool:
        """Generic write method for data backend

        Args:
            collection_type (str): **TODO**
            name (str): **TODO**
            data (Dict[str, Any]): Data to be written to the backend
            overwrite (bool, optional): Flag indicating if any existing 
                dictionary should be overwritten. Defaults to False.

        Returns:
            bool: _description_
        """
        return self.writer.write(collection_type, name, data, overwrite)

    def read_federation(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads the federation dictionary from the data backend

        Args:
            name (str): **TODO**

        Returns:
            Optional[Dict[str, Any]]: requested federation dictionary
        """
        return self.reader.read_federation(name)

    def read_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Reads the scenario dictionary from the data backend

        Args:
            name (str): **TODO**

        Returns:
            Optional[Dict[str, Any]]: requested scenario dictionary
        """
        return self.reader.read_scenario(name)

    def read(self, collection_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Generic read method for data backend

        Args:
            collection_type (str): Name of metadata collection from which to 
                read
            name (str): **TODO**

        Returns:
            Optional[Dict[str, Any]]: Requested data
        """
        return self.reader.read(collection_type, name)

    def list_federations(self) -> list[str]:
        """Provides list of federations with dictionaries in the data backend

        Returns:
            list[str]: List of federations dictionary names
        """
        return self.reader.list_federations()

    def list_scenarios(self) -> list[str]:
        """Provides list of scenarios with dictionaries in the data backend

        Returns:
            list[str]: List of scenario dictionary names
        """
        return self.reader.list_scenarios()

    def list_items(self, collection_type: str) -> list[str]:
        """**TODO**

        Args:
            collection_type (str): **TODO**

        Returns:
            list[str]: **TODO**
        """
        return self.reader.list_items(collection_type)

    def list_custom_collections(self) -> list[str]:
        """Provides the list of custom collection names in data backend

        Args:
            None

        Returns:
            list[str]: List of custom collection names
        """
        return self.reader.list_custom_collections()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if the backend is connected
        
        Args: 
            None

        Returns:
            bool: True if writer is connected to data backend
        """
        return self._is_connected


MetadataManager = MDDataManager
TimeSeriesManager = TSDataManager
