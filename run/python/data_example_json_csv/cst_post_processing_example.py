from cosim_toolbox.dbms import create_metadata_manager
from prettytable import PrettyTable
from pprint import pprint
from cosim_toolbox.dbms import create_timeseries_manager
from cosim_toolbox.dbms import TSRecord
from cosim_toolbox.dbms.csv_timeseries import (
    CSVTimeSeriesWriter,
    CSVTimeSeriesReader,
    CSVTimeSeriesManager,
    _CSVHelper,
)
from datetime import datetime
import time as t
import pandas as pd
import os


class post_process_example:

    def create_csv_files_meta_data(selfself,temp_dir):
        """Create the metadata database and load it with data

        Args:
            temp_dir (str): directory path to the folder that the metadata will be written to
        """
        # Create metadata dictionaries for the data contained in the csv files
        scenario1 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 20,
            "azimuth": 90,
            "units": "kW"
        }
        scenario2 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 20,
            "azimuth": 180,
            "units": "kW"
        }
        scenario3 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 20,
            "azimuth": 270,
            "units": "kW"
        }
        scenario4 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 30,
            "azimuth": 90,
            "units": "kW"
        }
        scenario5 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 30,
            "azimuth": 180,
            "units": "kW"
        }
        scenario6 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 30,
            "azimuth": 270,
            "units": "kW"
        }
        scenario7 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 40,
            "azimuth": 90,
            "units": "kW"
        }
        scenario8 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 40,
            "azimuth": 180,
            "units": "kW"
        }
        scenario9 = {
            "analysis": "rooftop solar",
            "federation": "rooftop solar federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-12-31T23:00:00",
            "docker": False,
            "solar tilt angle": 40,
            "azimuth": 270,
            "units": "kW"
        }

        md_mgr = create_metadata_manager(backend="json",location=temp_dir)
        md_mgr.connect()
        # Add dictionaries to the metadata data store
        md_mgr.write_scenario("scenario1", scenario1)
        md_mgr.write_scenario("scenario2", scenario2)
        md_mgr.write_scenario("scenario3", scenario3)
        md_mgr.write_scenario("scenario4", scenario4)
        md_mgr.write_scenario("scenario5", scenario5)
        md_mgr.write_scenario("scenario6", scenario6)
        md_mgr.write_scenario("scenario7", scenario7)
        md_mgr.write_scenario("scenario8", scenario8)
        md_mgr.write_scenario("scenario9", scenario9)
        scenario_names = md_mgr.list_scenarios()
        return md_mgr


    def read_csv_data_file_records(self,file_path):
        """Read the time series data from the csv result file

        Args:
            file_path (str): full path to the csv time series file to be read
        """
        if os.path.exists(file_path):
            #df = pd.read_csv(file_path)
            df = pd.read_csv(file_path)
            return df
        else:
            return None


    def add_csv_data_to_store(self, file_path, dir_path, analysis_name, scenario_name):
        """Convert a pandas dataframe to an array of ts_records

        Args:
            file_path (str): full path to the csv file that is to be read and added to the database
            dir_path (str): path to the directory where the time series database is located
            analysis_name (str): analysis name to be used for the time series being added
            scenario_name (str): scenario name to be used for the time series being added
        Returns:
            an array of ts_records which contains the time series dataset read from the csv files
        """
        csv_df = self.read_csv_data_file_records(file_path)
        ts_records = self.convert_dataframe_to_records(csv_df, scenario_name)
        manager = CSVTimeSeriesManager(
            location=dir_path, analysis_name=analysis_name
        )
        manager.connect()
        manager.write_records(ts_records)
        manager.disconnect()


    def convert_dataframe_to_records(self,ts_df,scenario_name):
        """Convert a pandas dataframe to an array of ts_records

        Args:
            file_path (str): full path to the csv file that is to be read and added to the database
            dir_path (str): path to the directory where the time series database is located
            analysis_name (str): analysis name to be used for the time series being added
            scenario_name (str): scenario name to be used for the time series being added
        Returns:
            an array of ts_records which contains the time series dataset read from the csv files
        """
        ts_records = []
        sim_seconds = 0
        first_time_string = ts_df.iloc[0].iloc[0]
        first_time_string = first_time_string.replace(", ", ", 2025 ")
        first_date_time = datetime.strptime(first_time_string, '%b %d, %Y %I:%M %p')
        for row in ts_df.iterrows():
            t_date_time_string = list(row)[1].iloc[0]
            t_date_time_string = t_date_time_string.replace(", ",", 2025 ")
            t_value = list(row)[1].iloc[1]
            t_date_time = datetime.strptime(t_date_time_string, '%b %d, %Y %I:%M %p')
            t_time_diff = t_date_time - first_date_time
            sim_seconds = t_time_diff.total_seconds()
            ts_records.append(TSRecord(
                real_time=t_date_time,
                sim_time=sim_seconds,
                scenario=scenario_name,
                federate="rooftop solar federation",
                data_name="System power generated",
                data_value=t_value)
            )
        return ts_records


    def write_csv_files_to_store(self, temp_dir, analysis_name):
        """Writes the csv time series data into the time series database

        Args:
            temp_dir (str): path to the time series database
            analysis_name (str): analysis name to be used for the time series being added
        """
        md_mgr = create_metadata_manager(backend="json",location=temp_dir)
        md_mgr.connect()
        scenario_names = md_mgr.list_scenarios()
        md_mgr.disconnect()
        for name in scenario_names:
            file_path = f"{temp_dir}/{name}.csv"
            self.add_csv_data_to_store(file_path,temp_dir,analysis_name,name)


    def create_random_meta_data(self):
        # Create metadata manager
        md_mgr = create_metadata_manager(backend="json")
        md_mgr.connect()

        # Create example metadata dictionaries
        example_scenario_20 = {
            "analysis": "example analysis",
            "federation": "example federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-01-14T00:00:00",
            "docker": False,
            "EV penetration": 0.2,
            "location": "Kansas"
        }
        example_scenario_40 = {
            "analysis": "example analysis",
            "federation": "example federation",
            "start_time": "2025-01-01T00:00:00",
            "stop_time": "2025-01-14T00:00:00",
            "docker": False,
            "EV penetration": 0.4,
            "location": "Kansas"
        }

        # Add dictionaries to the metadata data store
        md_mgr.write_scenario("EV 0.2", example_scenario_20)
        md_mgr.write_scenario("EV 0.4", example_scenario_40)

        # Read them back out
        scenario_names = md_mgr.list_scenarios()
        print(f"Scenario names {scenario_names}")

        scenario1 = md_mgr.read_scenario(name=scenario_names[0])
        print("Data from first listed scenario:")
        pprint(scenario1)

        md_mgr.disconnect()

    def create_random_time_series_data(self):
        # Creating a list of dummy time-series records
        # To make the data slightly consistent, we use the current real-time as the CST "real_time" timestamp
        # and then pause for one second after creating the record. The CST "sim_time" is ordinal time and will
        # have the same value as the CST "data_value" since they both increment by one each second.
        records = []
        for dummy_value in range(5):
            records.append(TSRecord(
                real_time= datetime.now(),
                sim_time=dummy_value,
                scenario="example_scenario",
                federate="dummy_fed",
                data_name="dummy_value",
                data_value=dummy_value)
            )
            t.sleep(0.2)

        # Setting up the time-series data manager that allows us to write and read data from the CSV data store
        with create_timeseries_manager(backend="csv", location="", analysis_name="example_analysis",
                                       database="cst") as mgr:
            # Add our made-up data to the data store
            mgr.write_records(records=records)

            # List the scenarios in the data store (should show "test_scenario" as being one)
            print(f"Scenarios: {mgr.list_scenarios()}")

            # List the data types in the data store
            print(f"Data types: {mgr.list_data_types()}")

            # Read all the data in the data store where the "scenario_name" in our scenario ("test_scenario)
            # Returns this as a Pandas DataFrame
            df = mgr.read_data(scenario_name="example_scenario")
            print(f"Data: {df}")


    def process_output(self,temp_dir,analysis_name):
        """processes and prints the values calculated from above

        Args:
            temp_dir (str): path to the time series database
            analysis_name (str): analysis name to be used for the time series being added
        """
        result_dict = {}
        scenario_results = []
        #creates the metadata database and adds the records
        md_mgr = self.create_csv_files_meta_data(temp_dir)
        md_mgr.connect()
        scenario_names = md_mgr.list_scenarios()
        md_mgr.disconnect()
        #creates the time series database and adds the records from the csv files
        self.write_csv_files_to_store(temp_dir,analysis_name)
        ts_manager = CSVTimeSeriesManager(
            location=temp_dir, analysis_name=analysis_name
        )
        ts_manager.connect()
        best_case_total = 0
        for name in scenario_names:
            result_dict = {}
            result_dict["name"] = name
            #calculate the scenario's total production
            df = ts_manager.read_data(scenario_name=name)
            total_production = df["data_value"].sum()
            result_dict["total_production"] = total_production
            #check scenario's total production against the last best case total
            if total_production > best_case_total:
                best_case_total = total_production
            #get start and end data time data for June 21, 2025
            start_date_time = datetime(2025, 1, 1, 0, 0, 0, 0)
            end_date_time = datetime(2025, 6, 21, 0, 0, 0, 0)
            diff_span = end_date_time - start_date_time
            #pull the time series data for only June 21, 2025 for the scenario
            df_june_data = ts_manager.read_data(scenario_name=name, start_time=diff_span.total_seconds(),duration=86400)
            #set a dictionary object to data values gathered above and add to an array of dictionary items
            row_index = df_june_data["data_value"].idxmax()
            june_max_production = df_june_data["data_value"][row_index]
            real_time = df_june_data["real_time"][row_index]
            sim_time = df_june_data["sim_time"][row_index]
            result_dict["june_real_time"] = real_time
            result_dict["june_sim_time"] = sim_time
            result_dict["june_max_production"] = june_max_production
            scenario_results.append(result_dict)
        ts_manager.disconnect()
        # Create and print the results table
        for result in scenario_results:
            percent_diff = (best_case_total - result["total_production"]) / result["total_production"]
            #result["percent_difference"] = str.format((percent_diff * 100),".0f"f"{value:.0f}")
            result["percent_difference"]  = f"{(percent_diff * 100):.0f}%"
        self.print_results_table(scenario_results)


    def print_results_table(self, result_list):
        """prints the results table to console

        Args:
            result_list (array of result dictionaries): array of dictionaries containing the scenario results
        """
        table = []
        result_entry = []
        result_entry = ['scenario', 'total_production', 'percent_difference', 'june_21_maximum_hour', 'june_21_maximum']
        table.append(result_entry)
        for result in result_list:
            result_entry = []
            result_entry.append(result["name"])
            result_entry.append(result["total_production"])
            result_entry.append(result["percent_difference"])
            result_entry.append(result["june_real_time"])
            result_entry.append(result["june_max_production"])
            table.append(result_entry)
        tab = PrettyTable(table[0])
        tab.add_rows(table[1:])
        print(tab)

if __name__ == "__main__":
    # ex_data.create_csv_files_meta_data("tests/SAM_data")
    # ex_data.write_csv_files_to_store("tests/SAM_data","rooftop solar")
    ex_data = post_process_example()
    ex_data.process_output("SAM_data","rooftop solar")
