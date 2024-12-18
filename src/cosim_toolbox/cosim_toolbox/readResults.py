import logging

from cosim_toolbox.dbResults import DBResults
from cosim_toolbox.readConfig import ReadConfig
from enum import Enum

logger = logging.getLogger(__name__)


class ValueType(Enum):
    STRING = 'HDT_STRING'
    DOUBLE = 'HDT_DOUBLE'
    INTEGER = 'HDT_INTEGER'
    COMPLEX = 'HDT_COMPLEX'
    VECTOR = 'HDT_VECTOR'
    COMPLEX_VECTOR = 'HDT_COMPLEX_VECTOR'
    NAMED_POINT = 'HDT_NAMED_POINT'
    BOOLEAN = 'HDT_BOOLEAN'
    TIME = 'HDT_TIME'
    JSON = 'HDT_JSON'


class ReadResults(DBResults):
    """
    alternative to ResultsDB
    """

    def __init__(self, scenario_name):
        super().__init__()
        self.is_connected = self.open_database_connections()
        self.scenario = ReadConfig(scenario_name)

    def __enter__(self):
        return self  # The object returned here will be assigned to the variable after 'as' in the 'with' statement

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_type is not None:
            print(f"An exception occurred: {exc_type}, {exc_value}")
        # Return False to propagate the exception, True to suppress it
        return False

    def open_database_connections(self, meta_connection: dict = None, data_connection: dict = None) -> bool:
        self.data_db = self._connect_logger_database(data_connection)
        if self.data_db is None:
            return False
        return True

    def close_database_connections(self, commit: bool = True) -> None:
        if self.data_db:
            if commit:
                self.data_db.commit()
            self.data_db.close()
        self.data_db = None

    def get_results(
            self,
            start_time=None,
            duration=None,
            federate_name=None,
            data_name=None,
            data_type: ValueType | str = ValueType.DOUBLE
    ):
        if isinstance(data_type, ValueType):
            data_type = data_type.value
        data_name_list = self.get_data_name_list(self.scenario.schema_name, data_type=data_type).to_numpy()
        federate_list = self.get_federate_list(self.scenario.schema_name, data_type=data_type).to_numpy()
        if data_name is not None and data_name not in data_name_list:
            logger.warning(f"data_name, {data_name}, not in {data_name_list}")
        if federate_name is not None and federate_name not in federate_list:
            logger.warning(f"federate_name, {federate_name} not in {federate_list}")
        if data_type not in self.hdt_type.keys():
            logger.warning(f"data_type, {data_type} not in {list(self.hdt_type.keys())}")
        return self.query_scenario_federate_times(start_time, duration, self.scenario_name, federate_name,
                                                  data_name, data_type)

    @property
    def string_df(self):
        return self.get_results(data_type=ValueType.STRING)

    @property
    def double_df(self):
        return self.get_results(data_type=ValueType.DOUBLE)

    @property
    def bool_df(self):
        return self.get_results(data_type=ValueType.BOOLEAN)

    @property
    def integer_df(self):
        return self.get_results(data_type=ValueType.INTEGER)

    @property
    def complex_df(self):
        return self.get_results(data_type=ValueType.COMPLEX)

    @property
    def vector_df(self):
        return self.get_results(data_type=ValueType.VECTOR)

    @property
    def complex_vector_df(self):
        return self.get_results(data_type=ValueType.COMPLEX_VECTOR)

    @property
    def named_point_df(self):
        return self.get_results(data_type=ValueType.NAMED_POINT)

    @property
    def time_df(self):
        return self.get_results(data_type=ValueType.TIME)

    @property
    def json_df(self):
        return self.get_results(data_type=ValueType.JSON)

    def close(self):
        self.close_database_connections()
