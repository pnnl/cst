"""
Created on 11/01/2024 

Data logger class that defines the basic operations of Python-based data logger in
Co-Simulation Toolbox but writes to MongoDB.

@authors:
trevor.hardy@pnnl.gov
"""

from os import environ
import logging
import pandas as pd
import datetime as dt
import inspect
from pymongo import MongoClient
from pymongo.collection import Collection

from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dbResults import DBResults

logger = logging.getLogger(__name__)

class DataLoggerMongo(DBResults):
    """Class for creating and using a data logger that writes to MongoDB

    In MongoDB, the abstraction hierarchy is:
        Database (SQL "database") contains
        Collections (SQL "table") contains
        Documents (SQL "records")

 
    The data models between the two databases are not identical as there is no
    "schema" in MongoDB. The methods reimplemented from the DBResults class
    are tweaked to account for these difference. Specifically, the data will
    be organized as follows:
        - Each CST scenario will have its own MongoDB database object
        - To organize the data from the federation, each federate will have its
        own MongoDB collection
        - Each publication from 

    Inside each scenario, there is one collection per federate.

    Each document is a single publication or message coming from a federate 
    and is formatted as follows:

    {
      metadata: { 
        federate: <federate name>,
        interfaceName: <publication or endpoint name>
        },
      timestamp: <Simulation time in ISO format "2021-05-18T00:00:00.000Z">,
      value: <numeric value or string>
    }

    Args:
        DBResults (_type_): _description_
    """

    # TODO: Everywhere mDB is being used directly in this file, the 
    # implemented functionality needs to be to TimeSeriesDB.py class in 
    # metadataDB.py

    def __init__(self):
        super.__init__()

    def open_database_connections(self, logger_connection: dict = None) -> bool:
        """Opens connection to MongoDB (metadata and data)

        Args:
            meta_connection (dict, optional): _description_. Defaults to None.

        Returns:
            bool: Indicates whether connection to database was established
        """
        # Pass in from federateLoggerMongo.py
        # if logger_connection is None:
        #     logger_connection = {
        #             "host": environ.get("MONGO_HOST", "mongo://localhost"),
        #             "port": environ.get("MONGO_POST", 27017),
        #             "dbname": f"{self.scenario_name}_ts_data",
        #             "user": environ.get("COSIM_USER", "worker"),
        #             "password": environ.get("COSIM_PASSWORD", "worker")
        #     }

        self.meta_db = super._connect_scenario_database(logger_connection)
        if self.meta_db is None:
            return False
        else:
            return True

    def close_database_connections(self) -> None:
        """Close connection to MongoDB
        """
        self.meta_db = None



    def check_version(self):
        """Gets the version of the MongoDB instance being used.
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented yet")

    def create_schema(self, scheme_name: str) -> None:
        """There is no equivalent of "schema" in MongoDB and calling this 
        method produces an exception.

        Args:
            scheme_name (str): Name of schema that will not be produced
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")

    def drop_schema(self, scheme_name: str) -> None:
        """There is no equivalent of "schema" in MongoDB and calling this 
        method produces an exception.

        Args:
            scheme_name (str): Name of schema that will not be produced
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")

    def remove_scenario(self, scenario_name: str) -> None:
        """Removes the scenario (MongoDB database) from MongoDB

        Args:
            scenario_name (str): _description_
        """
        # TODO this needs to be handled in the TimeSeriesDB class in metadataDB.py
        # Probably just need to move this line to an appropriately named method 
        # in that class
        self.meta_db.drop_database(scenario_name)

    def table_exist(self, collection_name: str) -> None:
        """Checks to see if the specified collection exists

        # TODO: once the purpose of this method in dataLogger.py is better
        defined, this method needs to be replimplemented to return an 
        appropriate value

        Args:
            collection_name (str): Collection name whose existance 
            is being checked
        """
        try:
            self.meta_db.validate_collection("random_collection_name")  # Try to validate a collection
        except self.meta_db.errors.OperationFailure:  # If the collection doesn't exist
            print("This collection doesn't exist")

    def make_logger_database(self, database_name: str) -> None:
        """Logger database was already created when the connection to the 
        database was established.

        Args:
            scheme_name (str): Name of schema that will not be produced
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")

    def get_select_string(self, scheme_name: str, data_type: str) -> str:
        """The "select" concept does not exist for NoSQL

        Args:
            scheme_name (str): Name of schema that will not be produced
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")

    def get_time_select_string(self, start_time: int, duration: int) -> str:
        """The "select" concept does not exist for NoSQL

        Args:
            scheme_name (str): Name of schema that will not be produced
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")
        

    def get_query_string(self, start_time: int,
                         duration: int,
                         scenario_name: str,
                         federate_name: str,
                         data_name: str,
                         ) -> str:
        """Creates the query dictionary used to access time-series data. 
        Despite the name, this is not a string but a dictionary object

        # TODO: The functionality specified below in the docstring needs to be
        # implemented
        For whoever implements this, this is what chatGPT says we should do:
        
        # Replace the following URI with your MongoDB connection string
        client = MongoClient("mongodb://localhost:27017/")

        # Access the database
        db = client.your_database_name

        # Access the time-series collection
        collection = db.sensorData

        # Define the timestamp range
        start_date = datetime(2023, 1, 1, 0, 0, 0)
        end_date = datetime(2023, 12, 31, 23, 59, 59)

        # Query the collection for documents within the timestamp range
        query = {
            "timestamp": {
                "$gte": start_date,
                "$lte": end_date
            }
        }


        Args:
            start_time (int): the starting time step to query data for
            duration (int): the duration in seconds to filter time data by
            If start_time and duration are entered as None then the query will return every
            time step that is available for the entered scenario, federate, pub_key,
            data_type combination.
            If start_time is None and a duration has been entered then all time steps that are
            less than the duration value will be returned
            If a start_time is entered and duration is None, the query will return all time steps
            greater than the starting time step
            If a value is entered for the start_time and the duration, the query will return all time steps
            that fall into the range of start_time to start_time + duration
            scenario_name (str): the name of the scenario to filter the query results by. If
            None is entered for the scenario_name the query will not use scenario_name as a filter
            federate_name (str): the name of the Federate to filter the query results by. If
            None is entered for the federate_name the query will not use federate_name as a filter
            data_name (str): - the name of the data to filter the query results by. If
            None is entered for the data_name the query will not use data_name as a filter

        Raises:
            NotImplementedError: _description_

        Returns:
            str: _description_
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented yet")
        
    def query_scenario_federate_times(self, start_time: int,
                                      duration: int,
                                      scenario_name: str,
                                      federate_name: str,
                                      data_name: str) -> pd.DataFrame:
        """Builds a query dictionary from the provided data, executes said
        query, and returns the values as a Pandas Dataframe

        Args:
            start_time (int): the starting time step to query data for
            duration (int): the duration in seconds to filter time data by
            If start_time and duration are entered as None then the query will return every
            time step that is available for the entered scenario, federate, pub_key,
            data_type combination.
            If start_time is None and a duration has been entered then all time steps that are
            less than the duration value will be returned
            If a start_time is entered and duration is None, the query will return all time steps
            greater than the starting time step
            If a value is entered for the start_time and the duration, the query will return all time steps
            that fall into the range of start_time to start_time + duration
            scenario_name (str): the name of the scenario to filter the query results by. If
            None is entered for the scenario_name the query will not use scenario_name as a filter
            federate_name (str): the name of the Federate to filter the query results by. If
            None is entered for the federate_name the query will not use federate_name as a filter
            data_name (str): - the name of the data to filter the query results by. If
            None is entered for the data_name the query will not use data_name as a filter

        Returns:
            pd.DataFrame: dataframe that contains the result records
            returned from the query of the database
        """

        qry_dict = self.get_query_string(start_time, 
                                         duration, 
                                         scenario_name, 
                                         federate_name, 
                                         data_name)
        # Projections filter data in MongoDB documents to just flagged values.
        projection = {
            "dataValue": 1  # Include the 'sensorValue' field in the output
        }
        results = self.meta_db.collection.find(qry_dict, projection)
        data_values = [document['dataValue'] for document in results]
        # TODO: figure out what the column name(s) should be
        return pd.DataFrame(data_values)
    
    def query_scenario_all_times(self, scenario_name: str, federate_name: str) -> pd.DataFrame:
        """This function queries data from the logger database filtered only by scenario_name 
        and the federate name
        
        # TODO: needs to be implementd

        Args:
            scenario_name (str): the name of the scenario to filter the query results by
            federate_name (str): name of federate from which all the data will be pulled

        Returns:
            pd.DataFrame: _description_
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented yet")


    def query_scheme_all_times(self, scheme_name: str, data_type: str) -> None:
        """Schemas are not implemented in MongoDB so this query is not supported.

        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")
    
    def query_scheme_federate_all_times(self, 
                                        scheme_name: str, 
                                        federate_name: str, 
                                        data_type) -> pd.DataFrame:
        """Since MongoDB doesn't have a scheme abstraction, this query
        cannot be implemented.
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")
    
    def get_schema_list(self) -> None:
        """No need to implement this as MongoDB doesn't have schemas.
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")
    
    def get_scenario_list(self) -> pd.DataFrame:
        """Scenarios are implemented as databases and all have a suffix of
        "_ts_data". This method queries the MongoDB instance for all database 
        names and returns the ones with this suffix as a Pandas DataFrame

        Returns:
            pd.DataFrame: DataFrame of scenarios
        """
        
        db_names = self.meta_db.database_names()
        ts_db_names = []
        for name in db_names:
            if name[-8:] == "_ts_data":
                ts_db_names.append(name)
        column_names = ["scenario"]
        return pd.DataFrame(ts_db_names, columns=column_names)
    
    def get_federate_list(self) -> pd.DataFrame:
        """Returns a list of federates for which data was collected in the
        current scenario (database)

        Args:
            scenario_name (str): Scenario in which data was collected

        Returns:
            pd.DataFrame: DataFrame of federates
        """
        federate_names = self.meta_db.list_collection_names()
        column_names = ["federate"]
        return pd.DataFrame(federate_names, columns=column_names)

    
    def get_data_name_list(self, scheme_name: str, data_type: str) -> pd.DataFrame:
        """No applicable to MongoDB
        """
        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented for MongoDB")
    
    def get_time_range(self, federate_name: str) -> pd.DataFrame:
        """Returns the maximum and minimum times. I'm not sure how to do this in 
        MongoDB. 

        Args:
            federate_name (str): Name of federate for which the max and min
            simulation times are being found.

        Returns:
            pd.DataFrame: Dataframe with minimum and maximum times
        """
        # column_names = ["min", "max"]
        # return pd.DataFrame(data, column_names)

        method_name = print(inspect.stack()[1][3])
        raise NotImplementedError(f"method {method_name} is not implemented yet")
    