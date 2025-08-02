# Data Management Design
To provide a variety of means for CoSim Toolbox (CST) users to write and read data out of their federates, a set of APIs has been developed. Though CST started out focused on centralized data collection with a Logger federate to write time-series data into Postgres and APIs to store structured data in MongoDB, it has been obvious through early user experience that providing alternative means of reading and writing data offered flexibility that offered benefits in some situations. 

## Data Management Abstractions
The architecture of the data management functionality in CST consists of three abstractions:

- TSRecord classes - a simply dataclass designed to hold a single time-series record.
- DataWriter classes - For each support data store type, a dedicated writer is defined to support writing data to the corresponding data store.
- DataReader classes - For each support data store type, a dedicated read is defined to support reading data from the corresponding data store.

The DataWrite and DataReader classes are abstract classes that must be implemented for each of the data store types. The methods defined in these classes are the minimum required for all DataWriters and DataReaders but more specific APIs can be implemented for a given data store type to suit its technological strengths and provide additional functionality. In many cases it will be common for a given implementation to instantiate a single DataWrite or DataReader class but the modularity of the classes supports multiple writers and readers.

### TSRecord Class 
The record class is a simple Python dataclass that is intended to document and define the datastypes needed for a single time-series record. With the type hinting provided by Python and its support in IDEs, it will be possible for developers to know if they are using the correct datatypes for each required field in a record without implementing formal checking. Implementing such checking may be implemented at a later time if found to be necessary but we recognize that performing data validation on every record may have significant computational cost. If such checking is implemented, an optional way of disabling will need to be supported to avoid paying this cost when there is high confidence the data types are correct.

### DataWriter Classes
DataWriter classes are responsible for establishing a connection to the data store defined by its "location" attribute, collecting TSRecord data an in internal buffer (TSDataWriters only), periodically writing the data buffer to the data store, and closing the connection to the data store. For TSDataWriters, this will require formating the TSRecord objects into a format appropriate for the data store technology to commit them to the store.

### DataReader Classes
DataReader classes are responsible for establishing a connection to the data store defined by its "location" attribute, reading data from data store and creating an appropriate representation, and closing the connection to the data store. For TSDataReaders, the returned data is formatted as a Pandas DataFrame. For MDDataReaders, the returned data is formated as a Python dictionary.

## Time-Series Data Store Considerations
The implementation of each data store technology requires consideration of how that particular technology structures data and how it manages the data on disk (or not). 

### Postgres 
Postgres is an implementation of a traditional SQL-style database and was the first data store type implemented in CST. All data is written to a single database named "cst". Data is organized where each analysis is representated by a Postgres "scheme" with the data organized in third-form normal with a unique table for each data type. The data types of almost all columns are fixed with the final "data value" column varying by table depending on the data being stored.

The PostgresDataWriter establishes a connection to the Postgres database and as necessary creates the database, schemas and tables necessary to write the data stored in one or more TSDataRecord objects. PostgresDataReader connects to the Postgres database and reads out the time-series data as specified by a few user-provided values (_e.g._ which federates, which scenario) and returns the queried value as a Pandas Dataframe.

Any custom time-series data that is stored in the Postgres data store prior to beginning the co-simulation for use during the co-simulation is stored in a custom-named table in the same schema (scenario) as the collected data. The columns of the table are identical to those in the TSDataRecord where the "federate" field can be used to define the source or type of data (_e.g._ "weather" or "historical prices") and the "data_name" field is used to identify the data more specifically.

There are some performance concerns with the current implementation of Postgres that, as of this writing, are being investigated.

### CSV files
To provide a faster alternative to the Postgres TSDataWriter for data collection, a simple CSV-based TSDataWriter provides data writing to local disk. This removes some of the advantages of a centralized data store in that data sharing becomes more complicated but provides faster read and write speeds of the data being collected.

To mimic the data structure of the Postgres database, a folder structure on local disk is used. In a user-specified directory, the CSVFileDataWriter looks for a folder with the analysis name and creates one if it doesn't exist. Inside that folder it looks for a folder with the CSVFileDataWriter's name and creates it if it doesn't exist. This is the target folder for writing the CSV files, one for each data type. The files are named `<data type>` and have the same columns as was used in the Postgres tables. CSVFileWriter takes one or more TSDataRecord objects and appends them to any existing files; new file is created if it doesn't exist when data needs to be written.

CSVFileReader supports reading any of these CVS and providing them as a Pandas Dataframe. The implemented APIs provide minimal filtering capabilities to allow only portions of the data in the CSV to be put into the Pandas Dataframe to help manage memory. Further filtering and aggregation can be performed using Pandas APIs.

Any custom time-series data that is stored in the CSV file data store prior to beginning the co-simulation for use during the co-simulation is stored as a CSV in a user-defined location within the folder structure. This allows maximum flexibility for how the federates in the co-simulation will use and access the data.

The columns of the table are identical to those in the TSDataRecord where the "federate" field can be used to define the source or type of data (_e.g._ "weather" or "historical prices") and the "data_name" field is used to identify the data more specifically. 

The folder structure as defined here is intended to prevent multiple federates from writing to the same file at the same time but such behavior may still occur, based on how each federate is implemented. This is one of the down-sides of a file-based datastore and extra care must be taken to avoid the writers and readers from stomping on each other and producing incomplete data sets.

Here is an example of the directory structure created by the CSVFileDataWriter:

```
├── example_analysis
│   └── federate_1
│       ├── hdt_boolean.txt
│       ├── hdt_double.txt
│       └── hdt_string.txt
```

## Metadata 
Metadata is managed in the same was as time-series data. Where time-series data is tabular in nature, meta-data is structured in a less rigid manner such as what can be achieved in a Python dictionary or JSON file. This is called "structured" data (as opposed to the time-seried "tabular" data).

Just like storing time-series data, there are centralized, data-base approaches and file-based approaches to managing the data.

### MongoDB
MongoDB provides a centralized database for storing structured data. CST creates and uses a database named "cst" and creates two MongoDB "collections": "federations" and "scenarios". 

"federations" contains user-named dictionaries that define metadata for all federates used in a given co-simulation; the fields in this dictionary are defined in **TODO**. This dictionary also includes a "HELICS_config" item which is the entirety of the required HELICS configuration file. **TODO** Mitch recently implemented a federation configuration API that might have a HELICSConfig class that should be referenced here.

"scenarios" contains dictionaries that define the metadata for a given scenario. This includes definitions for the start and stop time and which federation definition from the "federations" collection will be used to define the federates.

User added structured data outside the "federations" and "scenarios" collections can also be accessed using a provided API that just looks for a user-provided unique collection and/or dictionary name. 

### JSON files
Similar to how the CSVFileDataWrite provides a file-based option for storing the time-series data, JSONFileDataWriter provides a way to write out the metadata to a file on disk. In a user-specified location, the JSONFileDataWriter will look for a folder with the analysis name and creates one if it doesn't exist. Inside that folder it will create "federations" and "scenarios" folders. Inside the "federations" folder, each dictionary that defines the federation will be written out as a single JSON file. Similarly, for each dictionary in the "scenarios" a single JSON file will be written to disk.

JSONFileDataReader looks in a specified location for a "federations" folder and/or "scenarios" folder and based on the provided scenario or federation name, will read in the appropriate JSON and provide it as a dictionary.

User added structured data outside the "federations" and "scenarios" folder can also be accessed using a provided API that just looks for a user-provided unique folder and/or file name. 

The folder structure as defined here is intended to prevent multiple federates from writing to the same file at the same time but such behavior may still occur, based on how each federate is implemented. This is one of the down-sides of a file-based datastore and extra care must be taken to avoid the writers and readers from stomping on each other and producing incomplete data sets.

## Implementations

### Joint Readers and Writers
Under the assumption that it will be common for an instance to use the reader and writer for a given data store, classes have been defined that hold a joint reader and writer instance. In these cases, this joint class instantiates the reader and writer it needs and passes in the connection to the data store so that all APIs implemented by the reader and writer have direct access to the store (and don't need to ask the parent class object for said connection).

It is expected that these joint reader and writer classes will be the most common implementation of readers and writer objects.

### Federate Class
The CST Federate class implements a joint reader and writers one for a time series data store and one for a metadata data store. The types of readers and writers are defined at instantiation of the Federate object by parameters passed in to the `_init_()` method and joint reader and writer is instantiated then.

The Federate class will use the metadata reader and writer to get its configuration information, read and potentially edit any other structured data (_e.g._ custom scenario data, other use-case specific configuration data). This is most likely to occur during the federate's setup but may also occur throughout or at the end of the federate's main co-simulation loop.

The Federate's connection to the time-series data store is most likely to be used during the main co-simulation loop. Any output data that is collected in the data store will be written during the main co-simulation loop. The federate implements a list where TSDataRecords are appended as they are generated and when the list reaches a certain size the list is committed to the data store and reset to receive additional data. Prior to leaving the federation, the federate also commits any last data in the list, regardless of the size of the list.

The federate may also have need to pull data from the time-series store and the reader would be used to do this. 

### data_collector.py
"data_collector.py" performs data collection for all the federates in the simulation that do not use the CST Federate class. The data_collector is configurable but generally subscribes to all publications and endpoints and when any federate produces any new output data via HELICS, HELICS provides a copy to the data_collector who in turn commits it to the data store. If the implementation of the federate class is done properly, the built-in implementation of that class may be sufficient to achieve this functionality with only the configuration choice of which data to collect needing to be defined.

## Pending Design Questions

### Database-like operations for file-based readers?
For non-database readers (_e.g._ CSV), do we want to support query-like methods where the reader will be responsible for filtering data from the CSV before committing it into the Pandas dataframe that is returned to the user? It probably wouldn't be too hard but may not be computationally efficient.