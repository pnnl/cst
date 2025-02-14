import json
import sys, os
import logging
import numpy as np
import pandas as pd
import h5py
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

from cosim_toolbox.dbResults import DBResults

# These defaults will create query_info.json.
# We recommend not editing the defaults here (unless changing the default)
# Edit the query_info.json directly (minimizes changes in the GitLab repo)
query_defaults = {
    "start_time": "2032-01-01 00:00:00",
    "stop_time": None,
    "time_type": "real_time",
    "scenario_name": "osw_lmp_test_scenario",
    "schema_name": "osw_test_schema",
    "data_type": "string",
    "columns": "*",
    "column_options": [
        "real_time",
        "sim_time",
        "scenario",
        "federate",
        "data_name",
        "data_value"
      ],
    "da_price": True,
    "da_reserve": True,
    "rt_price": True,
    "rt_dispatch": True,
    "buses": [
        4005,
        4202,
        3911,
        3903,
        3902
      ],
    "generators": [
        "JOHN_DAY",
        "WCASCADE",
        "COTTONWOO",
        "TESLA",
        "MOSSLAND"
      ],
    "areas": "NORTH",
    "reserves": [
        "regulation_up_price",
        "regulation_down_price",
        "flexible_ramp_up_price",
        "flexible_ramp_down_price"
        ]
}

def get_save_quantities(query_info):
    """
    Parses the query info dictionary to return a list of desired quantities to save.
    Options are:
      1. da_price: DA prices (LMP by bus)
      2. da_reserve: DA reserves (MCP by area)
      3. rt_price: RT prices (LMP by bus)
      4. rt_dispatch: RT dispatch (MW by generator)

    Args:
        query_info (dict): Query information. Keys include schema, data, and scenario names, start/stop times,
                           buses, areas, generators, and booleans for DA, RT, reserves, and dispatch

    Returns:
        quantities (list): List of desired quantities to save
    """
    options = ['da_price', 'da_reserve', 'rt_price', 'rt_dispatch']
    quantities = []
    for option in options:
        # Query info saves a boolean T/F for each option
        if query_info[option]:
            quantities.append(option)
    if len(quantities) == 0:
        raise ValueError(f"No quantities selected to save. At least one of {options} is required.")
    return quantities

def create_time_clause(start_time, stop_time, time_type):
    """
    Creates a clause restricting time range.

    Args:
        query_string (str): A SQL query string to retrieve the requested information
        start_time (str, float, or None): Start time of the time range
        stop_time (str, float, or None): Stop time of the time range
        time_type (str): The time type of the time range (one of 'real_time', 'sim_time')
    """
    assert time_type in ['real_time',
                         'sim_time'], f"Specified time type {time_type} not supported. Use 'real_time' or 'sim_time'"
    time_clause = ""
    if start_time is not None:
        time_clause += f"AND {time_type} >= '{start_time}' "
    if stop_time is not None:
        time_clause += f"AND {time_type} <= '{stop_time}' "
    return time_clause

def create_reserve_clause(reserve, area):
    """
    Creates a clause adding the reserves by area
    """
    # Check that the reserve is one of the options we are saving
    reserve_options = ['regulation_up_price', 'regulation_down_price', 'flexible_ramp_up_price',
                      'flexible_ramp_down_price']
    assert reserve in reserve_options, f"Specified reserves {reserve} not available. Use one of {reserve_options}"
    # Build and return the clause
    return f"data_name LIKE '%{reserve}_{area}' "

def create_quantity_clause(query_info, quantity):
    """
    Creates a clause collecting the appropriate quantity (LMP, MCP, dispatch) by bus/area/generator
    """
    quantity_clause = "AND ( "
    # DA and RT prices are arranged by bus
    if 'price' in quantity:
        # Get bus name(s) and add to quantity clause
        buses = query_info['buses']
        if isinstance(buses, str):
            buses = [buses]
        for bus in buses:
            quantity_clause += f"data_name LIKE '%{quantity}_{bus}' "
            if bus != buses[-1]:
                quantity_clause += "OR "
            else:
                quantity_clause += ") "
    if 'reserve' in quantity:
        # Get reserve and area type(s) (if single type string, convert to length 1 list)
        reserves = query_info['reserves']
        if isinstance(reserves, str):
            reserves = [reserves]
        areas = query_info['areas']
        if isinstance(areas, str):
            areas = [areas]
        for reserve in reserves:
            for area in areas:
                quantity_clause += create_reserve_clause(reserve, area)
                if area == areas[-1] and reserve == reserves[-1]:
                    quantity_clause += ") "
                else:
                    quantity_clause += "OR "
    if 'dispatch' in quantity:
        # Get generator names and add to quantity clause
        generators = query_info['generators']
        if isinstance(generators, str):
            generators = [generators]
        for generator in generators:
            quantity_clause += f"data_name LIKE '%{quantity}_{generator}%' "
            if generator != generators[-1]:
                quantity_clause += "OR "
            else:
                quantity_clause += ") "
    return quantity_clause


def create_query_string(query_info: dict, quantity: str) -> str:
    """
    Creates a SQL query string from the given query info

    Args:
        query_info (dict): Query information. Keys include schema, data, and scenario names, start/stop times,
                           buses, areas, generators, and booleans for DA, RT, reserves, and dispatch
        quantity (str): The desired quantity to retrieve

    Returns:
        query_string (str): A SQL query string to retrieve the requested information
    """
    # Collect variables from query_info
    schema_name = query_info["schema_name"]
    data_type = query_info["data_type"]
    scenario_name = query_info["scenario_name"]
    columns = query_info["columns"]
    # If supplying a list of columns, convert it to a space-separated string
    if isinstance(columns, list):
        columns = " ".join(columns)
    query_string = (f"SELECT {columns} from {schema_name}.hdt_{data_type} "
                    f"WHERE scenario='{scenario_name}' ")
    # Restrict date range (if no start/stop passed, will get all available dates)
    start_time, stop_time = query_info["start_time"], query_info["stop_time"]
    time_type = query_info["time_type"] # can be real_time (str 'YYYY-mm-dd HH:MM:SS) or sim_time (float seconds)
    if start_time is not None or stop_time is not None:
        query_string += create_time_clause(start_time, stop_time, time_type)
    # Add quantity-specific query
    query_string += create_quantity_clause(query_info, quantity)
    # Order by timestamp
    query_string += "ORDER BY real_time ASC"

    return query_string

def save_h5(h5_dict, fname='all_results.h5', use_columns=['real_time', 'scenario', 'data_name', 'data_value']):
    """
    Saves the values in the h5_dict to the given filename (in the 'data' folder)

    Args:
        h5_dict (dict): Dictionary to save.
                        Accepted format is either h5_dict = {quantity_name : quantity_dataframe}
                                             OR   h5_dict = {quantity_name : {column_name: data_array}
    """
    os.makedirs('data', exist_ok=True)
    if not fname.endswith('.h5'):
        fname += '.h5' # Add extension if not specified
    # Open the h5 file for writing
    f = h5py.File(f'data/{fname}', 'w')
    # Loop through all quantities
    for quantity, qty_value in h5_dict.items():
        # Each quantity is a unique group
        grp = f.create_group(quantity)
        if isinstance(qty_value, dict):
            generator = qty_value.keys()
        elif isinstance(qty_value, pd.DataFrame):
            generator = qty_value.columns
        else:
            raise TypeError(f'h5_dict value type is {type(qty_value)}: must be either dict or pd.DataFrame')
        # Loop through columns in the dataframe/keys in dict, restricting to use_columns
        for column in generator:
            if column in use_columns:
                if isinstance(qty_value, dict):
                    data = qty_value[column]
                elif isinstance(qty_value, pd.DataFrame):
                    data = qty_value.loc[:, column].values
                # For the timestamp, convert all to string format
                if column == 'real_time':
                    new_data = []
                    for i in range(len(data)):
                        new_data.append(np.datetime_as_string(data[i], unit='s'))
                    # H5 doesn't accept unicode (the default). Covert to fixed-length string
                    data = np.array(new_data).astype('S19') # 19 characters for the datatime in seconds format
                # Ignore empty data, otherwise create a dataset inside this group
                if len(data) > 0:
                    grp.create_dataset(column, data=data)

def read_h5(groups=None, fname='all_results.h5', fixed_fname=False, return_format='dataframe'):
    """
    Reads h5 data and returns a nested dictionary a dictionary of dataframes, or a specified dict or dataframe

    Args:
        groups (str): Option to specify a particular h5 group. If None (default) returns all in a dictionary
        fname (str): name of file to open
        fixed_fname (bool): if true, does not append 'data/' to fname
        return_format (str): The type (dict or dataframe) to use for each group entry
    returns:
        h5_data (dict or pd.DataFrame): the data, either as a dictionary of groups or as a single group
    """
    # TODO: Need to do better type handling with h5 datasets. All are byte strings b'....'
    if not fname.endswith('.h5'):
        fname += '.h5' # Add extension if not specified
    if not fixed_fname:
        fname = f'data/{fname}'
    # Open the h5 file for writing
    f = h5py.File(fname, 'r')
    # Parse contents into output
    h5_data = {}
    for group_name in f.keys():
        grp = f[group_name]
        grp_values = {}
        for dataset_name in grp.keys():
            grp_values[dataset_name] = grp[dataset_name]
        # If using a dataframe, put the dict into a dataframe
        if return_format.lower() == 'dataframe':
            grp_values = pd.DataFrame(grp_values)
            # Set time as index, if it is available
            if 'real_time' in grp_values.columns:
                grp_values.set_index('real_time', inplace=True)
                grp_values.index.name = 'real_time'
        h5_data[group_name] = grp_values
    if groups is None:
        return h5_data
    else:
        if groups in h5_data.keys():
            return h5_data[groups]
        else:
            raise ValueError(f'Group {groups} not found in h5_data')

if __name__ == "__main__":
    # Create the query_info.json file from defaults, if it doesn't exist
    if not os.path.isfile('query_info.json'):
        with open('query_info.json', 'w') as f:
            json.dump(query_defaults, f, indent=4)
        print("Created file `query_info.json`\nEdit this file to customize your query")
        exit(0)
    # Load the query_info json file (can be edited to adjust queries)
    with open('query_info.json', 'r') as f:
        query_info = json.load(f)
    # Determine which quantities we are saving. Then loop through and load each one at a time
    save_quantities = get_save_quantities(query_info)
    h5_dict = {}
    for quantity in save_quantities:
        # Convert the json file to a SQL query string and display for the user to verify correct query
        query_string = create_query_string(query_info, quantity)
        print("Executing query:\n", query_string)
        # print_query_info(query_info)
        # Initialize a DBResults object and connect to the database
        dbresults = DBResults()
        dbresults.open_database_connections()
        dbresults.check_version()
        # Run the query
        dataframe = dbresults.execute_query(query_string)
        # Check the memory size to avoid saving really huge files
        memory_bytes = sys.getsizeof(dataframe)
        memory_MB = memory_bytes / 1024 / 1024
        memory_limit = 100 # Units of MB
        if memory_MB > 10:
            logger.warning(f"High memory ({memory_MB:0.2f}MB) required for saving CSV")
        if memory_MB > memory_limit:
            raise MemoryError(f"Required memory ({memory_MB:0.2f}MB) exceeds imposed memory limit ({memory_limit:0.2f}MB)"
                              f"Increase limit, divide CSV into multiple files, or use H5 format")
        # Save the results to CSV in th data folder
        os.makedirs('data', exist_ok=True)
        # Note this always overwrites an existing. Could generate more files, but that could also get cumbersome
        dataframe.to_csv(f'data/{quantity}_results.csv', index=False)
        h5_dict[quantity] = dataframe
    # with open('data/all_results.h5', 'w') as f:
    save_h5(h5_dict, fname='all_results.h5')
