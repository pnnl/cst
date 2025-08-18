"""
Created 30 Nov 2023

Metadata Database API implementation

@author Trevor Hardy
"""
import os
import typing
import logging

from pymongo import MongoClient
import gridfs
import bson

import cosim_toolbox as env
from cosim_toolbox.helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)

def federation_database(clear: bool = False) -> None:
    """Removes existing default CST databases and creates new ones.
    """
    db = DBConfigs(env.cst_mongo, env.cst_mongo_db)
    logger.info("Before: ", db.update_collection_names())
    if clear:
        db.db[env.cst_federations].drop()
        db.db[env.cst_scenarios].drop()
    db.add_collection(env.cst_scenarios)
    db.add_collection(env.cst_federations)
    logger.info("After clear: ", db.update_collection_names())


class DBConfigs:
    """
    Provides methods to read and write to the metadata database.

    TODO: Update method names so they don't refer to "dictionaries" or
    "documents" but are instead using the CST terminology. We might need to
    add some of these terms into the Mongo documents so that they can be
    queried with the same parameters as we use in the time-series database.
    Mongo has databases, collections, and documents. Postgres has databases,
    schemes, and tables. Should these line up one-to-one?
    """
    _cst_name = 'cst_007'

    def __init__(self, uri: str = None, db_name: str = None) -> None:
        self.collections = None
        self.db_name, self.client = self._connect_to_database(uri, db_name)
        self.db = self.client[self.db_name]
        self.fs = gridfs.GridFS(self.db)

    def __del__(self):
        if self.client is not None:
            self.client.close()

    @staticmethod
    def _open_file(file_path: str, mode: str = 'r') -> None | typing.IO:
        """Utility function to open file with reasonable error handling.

        Args:
            file_path (str): Path to file to be opened
            mode (str, optional): File opening style. Defaults to 'r'.

        Returns:
            typing.IO: File handle
        """
        try:
            fh = open(file_path, mode)
        except IOError:
            logger.error('Unable to open {}'.format(file_path))
        else:
            return fh

    @staticmethod
    def _connect_to_database(uri: str = None, db: str = None) -> tuple:
        """Sets up connection to server port for mongodb

        Args:
            uri (str, optional): URI for MongoDB. Defaults to None.
            db (str, optional): Name of database in MongoDB to use.
            Defaults to None.

        Returns:

        Returns:
            tuple: name of database as string and MongoDB client object
        """
        # Set up default uri_string to the server Trevor was using on the EIOC
        if uri is None:
            uri = env.cst_mongo
        if db is None:
            db = env.cst_mongo_db
        # Set up connection
        uri = uri.replace('//', '//' + env.cst_user + ':' + env.cst_password + '@')
        client = MongoClient(uri + '/?authSource=' + db + '&authMechanism=SCRAM-SHA-1')
        # Test connection
        try:
            client.admin.command('ping')
            logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as ex:
            logger.info(ex)

        return db, client

    def _check_unique_doc_name(self, collection_name: str, new_name: str) -> bool:
        """
        Checks to see if the provided document name is unique in the specified
        collection.

        Doesn't throw an error if the name is not unique and lets the calling
        method decide what to do with it.
        """
        ret_val = True
        for doc in (self.db[collection_name].find({}, {"_id": 0, self._cst_name: 1})):
            if doc.__len__():
                if doc[self._cst_name] == new_name:
                    ret_val = False
        return ret_val

    def add_file(self, file: str, conflict: str = 'fail', name: str = None) -> None:
        """
        Gets file from disk and adds it to the dbConfigs for all federates
        to use.

        The "name" parameter is optional. If provided, the file will be
        stored by that name in the database. If omitted, the name of the
        file itself will be used.

        MongoDB allows files to have the same name and creates unique IDs.
        By default, this method will produce an error if the name of the
        file being added already exists in the file storage. This can
        behavior can be altered by specifying the "conflict" parameter
        to a different value. Supported values are
            "fail" - Produces an error if the file name being added
                     already exists in the database
            "overwrite" - New file overwrites the existing one
            "add version" - New file is added as a version of
                            the existing one.
        """
        if not name:
            path, file = os.path.split(file)
            name = file
        fh = self._open_file(file, mode='rb')

        # Check for unique filename
        db_file = self.fs.files.find({'filename': name})
        if db_file:
            if conflict == "fail":
                raise NameError(f"File '{name}' already exists, set 'conflict' to 'overwrite' to overwrite it.")
            if conflict == "overwrite":
                logger.warning(f"File {name} being overwritten.")
            if conflict == "add version":
                logger.warning(f"New version of file {name} being added.")
            else:
                raise NameError(f"Invalid value for conflict resolution '{name}',"
                                f"must be 'fail', 'overwrite' or 'add version' ")
        self.fs.put(fh, filename=name)

    def get_file(self, name: str, disk_name: str = None, path: str = None) -> gridfs.GridOut:
        """
        Pulls a file from the dbConfigs by "name" and optionally writes it to
        disk. This method only gets the latest version of the file (if
        multiple versions exist).

        If "disk_name" is specified, that name will be used when writing the
        file to disk; otherwise the file name as specified in the dbConfigs
        will be used. If "path" is not specified, the file is not written to
        disk. If it is, the file is written at the location specified by "path"
        using the provided "disk_name".
        """
        db_file = self.fs.files.find({'filename': name})
        if not db_file:
            raise NameError(f"File '{name}' does not exist in dbConfigs.")
        else:
            db_file = self.fs.get_last_version(filename=name)
            if path:
                if disk_name:
                    path = os.path.join(path, disk_name)
                else:
                    path = os.path.join(path, name)
                fh = self._open_file(path, 'wb')
                fh.write(db_file)
            return db_file

    def remove_collection(self, collection_name: str):
        """
        Removes the collection from the dbConfigs specified by "collection_name"
        """
        self.db[collection_name].drop()
        self.update_collection_names()

    def remove_document(self, collection_name: str,
                        object_id: bson.objectid.ObjectId = None,
                        dict_name: str = None) -> None:
        """
        Remove the document specified by "object_id" or "dict_name" from the
        collection specified by "collection_name".
        """
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            logger.warning("Using provided object ID (and not provided name) to remove document.")
            self.db[collection_name].delete_one({"_id": object_id})
        elif dict_name is not None:
            self.db[collection_name].delete_one({self._cst_name: dict_name})
        elif object_id is not None:
            self.db[collection_name].delete_one({"_id": object_id})
        # TODO: Add check for success on delete.

    def remove_dict(self, collection_name: str,
                    dict_name: str) -> None:
        """
        Remove the dictionary specified by "dict_name" from the
        collection specified by "collection_name".
        """
        self.db[collection_name].delete_one({self._cst_name: dict_name})
        # TODO: Add check for success on delete.

    def add_collection(self, name: str):
        """
        Collections don't really exist in MongoDB until at least one document
        has been added to the collection. This method adds a small identifier
        JSON to fill this role.
        """
        id_dict = {"collection name": name}
        collection = self.db[name]
        collection.insert_one(id_dict)
        self.update_collection_names()
        return collection

    def update_collection_names(self) -> list:
        """
        Updates the list of collection names in the db object from the database.
        As you can see in the code below, this is pure syntax sugar.
        """
        self.collections = self.db.list_collection_names()
        return self.collections

    def get_collection_document_names(self, collection_name: str) -> list:
        """
        Provides list of document names in collection specified by
        "collection_name"
        """
        doc_names = []
        for doc in (self.db[collection_name].find({}, {"_id": 0, self._cst_name: 1})):
            if doc.__len__():
                doc_names.append(doc[self._cst_name])
        return doc_names

    def get_dict_key_names(self, collection_name: str, doc_name: str) -> list:
        """
        Provides the list of keys for the document (dictionary) specified
        by "doc_name" in the collection "collection_name".
        """
        # TODO: Add input validation that the collection and document do exist
        if collection_name not in self.collections:
            raise NameError(f"Collection '{collection_name}' does not exist.")
        if doc_name not in self.get_collection_document_names(collection_name):
            raise NameError(f"Document '{doc_name}' does not exist in collection {collection_name}.")
        doc = self.db[collection_name].find({self._cst_name: doc_name})
        return doc[0].keys()

    def add_dict(self, collection_name: str, dict_name: str, dict_to_add: dict) -> str:
        """
        Adds the Python dictionary to the specified MongoDB collection as a
        MongoDB document. Checks to make sure another document does not exist
        by that name; if it does, throw an error.

        To allow later access to the document by name,
        the field "cst_007" is added to the dictionary before adding
        it to the collection (the assumption is that "cst_007" will
        always be a unique field in the dictionary).
        """
        if self._check_unique_doc_name(collection_name, dict_name):
            dict_to_add[self._cst_name] = dict_name
        else:
            raise NameError(f"{dict_name} is not unique in collection {collection_name} and cannot be added.")
        obj_id = self.db[collection_name].insert_one(dict_to_add).inserted_id

        return str(obj_id)

    def get_dict(self, collection_name: str,
                 object_id: bson.objectid.ObjectId = None,
                 dict_name: str = None) -> dict:
        """
        Returns the dictionary in the database based on the user-provided
        object ID or name.

        User must enter either the dictionary name used or the object_ID that
        was created when the dictionary was added but not both.
        """
        doc = None
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            logger.warning("Using provided object ID (and not provided name) to get dictionary.")
            doc = self.db[collection_name].find_one({"_id": object_id})
        elif dict_name is not None:
            doc = self.db[collection_name].find_one({self._cst_name: dict_name})
            if not doc:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be retrieved.")
        elif object_id is not None:
            doc = self.db[collection_name].find_one({"_id": object_id})
        # Pulling out the DBConfigs secret name field that was added when we put
        #   the dictionary into the database. Will not raise an error if
        #   somehow that key does not exist in the dictionary
        if doc:
            doc.pop(self._cst_name, None)
            doc.pop("_id", None)
        return doc

    def update_dict(self, collection_name: str,
                    updated_dict: dict,
                    object_id: bson.objectid.ObjectId = None,
                    dict_name: str = None) -> object:
        """
        Updates the dictionary on the database (under the same object_ID/name)
        with the passed in updated dictionary.

        User must enter either the dictionary name used or the object_ID that
        was created when the dictionary was added but not both.
        """
        result = None
        updated_dict[self._cst_name] = dict_name
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be modified.")
        elif dict_name is not None and object_id is not None:
            logger.warning("Using provided object ID (and not provided name) to update database.")
            result = self.db[collection_name].replace_one({"_id": object_id}, updated_dict)
        elif dict_name is not None:
            doc = self.db[collection_name].find_one({self._cst_name: dict_name})
            if doc:
                result = self.db[collection_name].replace_one({"_id": doc['_id']}, updated_dict)
            else:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be updated.")
        elif object_id is not None:
            result = self.db[collection_name].replace_one({"_id": object_id}, updated_dict)
        return result

    @staticmethod
    def scenario(schema_name: str, federation_name: str, start: str, stop: str, docker: bool = False) -> dict:
        """
        Creates a properly formatted CoSimulation Toolbox scenario document
        (dictionary), using the provided inputs.
        """
        return {
            "schema": schema_name,
            "federation": federation_name,
            "start_time": start,
            "stop_time": stop,
            "docker": docker
        }

    def store_federation_config(self, name: str, config: dict) -> None:
        self.remove_dict(env.cst_federations, name)
        self.add_dict(env.cst_federations, name, config)

    def store_scenario(self,
            scenario_name: str, schema_name: str, federation_name: str,
            start: str, stop: str, docker: bool = False) -> None:
        scenario = self.scenario(schema_name, federation_name, start, stop, docker)
        self.remove_dict(env.cst_scenarios, scenario_name)
        self.add_dict(env.cst_scenarios, scenario_name, scenario)

    def get_scenario(self, scenario_name) -> dict:
        if scenario_name not in self.list_scenarios():
            logger.error(f"{scenario_name} not found in {self.list_scenarios()}.")
        return self.get_dict(env.cst_scenarios, None, scenario_name)

    def get_federation_config(self, federation_name) -> dict:
        if federation_name not in self.list_federations():
            logger.error(f"{federation_name} not found in {self.list_federations()}.")
        return self.get_dict(env.cst_federations, None, federation_name)

    def list_scenarios(self) -> list:
        return self.get_collection_document_names(env.cst_scenarios)

    def list_federations(self) -> list:
        return self.get_collection_document_names(env.cst_federations)

    # TODO: discuss what might be useful for extra user defined data
    def store_user_defined_config(self, name):
        pass

    def get_user_defined_config(self, name):
        pass


def mytest1():
    """
    Main method for launching metadata class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community:
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container:
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = DBConfigs(env.cst_mongo, env.cst_mongo_db)
    logger.info(db.update_collection_names())
    db.add_collection(env.cst_scenarios)
    db.add_collection(env.cst_federations)

    t1 = HelicsMsg("Battery", period=30)
    t1.config("core_type", "zmq")
    t1.config("log_level", "warning")
    t1.config("period", 60)
    t1.config("uninterruptible", False)
    t1.config("terminate_on_error", True)
    t1.config("wait_for_current_time_update", True)
    t1.pubs_e("Battery/EV1_current", "double", "A", True)
    t1 = {
        "image": "python/3.11.7-slim-bullseye",
        "federate_type": "value",
        "time_step": 120,
        "HELICS_config": t1.write_json()
    }

    diction = {
        "federation": {
            "Battery": t1
        }
    }

    scenario_name = "ME30"
    schema_name = "Tesp"
    federate_name = "BT1"
    db.add_dict(env.cst_federations, federate_name, diction)

    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(env.cst_scenarios, scenario_name, scenario)

    logger.info(db.get_collection_document_names(env.cst_scenarios))
    logger.info(db.get_collection_document_names(env.cst_federations))
    logger.info(db.get_dict_key_names(env.cst_federations, federate_name))
    logger.info(db.get_dict(env.cst_federations, None, federate_name))


def mytest2():
    """
    Main method for launching metadata class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community:
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container:
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = DBConfigs(env.cst_mongo, env.cst_mongo_db)
    logger.info(db.update_collection_names())
    db.add_collection(env.cst_scenarios)
    db.add_collection(env.cst_federations)

    t1 = HelicsMsg("Battery", period=30)
    t1.config("core_type", "zmq")
    t1.config("log_level", "warning")
    t1.config("period", 60)
    t1.config("uninterruptible", False)
    t1.config("terminate_on_error", True)
    t1.config("wait_for_current_time_update", True)
    t1.pubs_e("Battery/EV1_current", "double", "A", True)
    t1.subs_e("EVehicle/EV1_voltage", "double", "V", True)
    t1 = {
        "image": "python/3.11.7-slim-bullseye",
        "federate_type": "value",
        "time_step": 120,
        "HELICS_config": t1.write_json()
    }

    t2 = HelicsMsg("EVehicle", period=30)
    t2.config("core_type", "zmq")
    t2.config("log_level", "warning")
    t2.config("period", 60)
    t2.config("uninterruptible", False)
    t2.config("terminate_on_error", True)
    t2.config("wait_for_current_time_update", True)
    t2.subs_e("Battery/EV1_current", "double", "A", True)
    t2.pubs_e("EVehicle/EV1_voltage", "double", "V", True)
    t2 = {
        "image": "python/3.11.7-slim-bullseye",
        "federate_type": "value",
        "time_step": 120,
        "HELICS_config": t2.write_json()
    }
    diction = {
        "federation": {
            "Battery": t1,
            "EVehicle": t2
        }
    }

    scenario_name = "TE30"
    schema_name = "Tesp"
    federate_name = "BT1_EV1"
    db.add_dict(env.cst_federations, federate_name, diction)

    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(env.cst_scenarios, scenario_name, scenario)

    scenario_name = "TE100"
    # seems to remember the scenario address, not the value so reinitialize
    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-10T15:31:27", True)
    db.add_dict(env.cst_scenarios, scenario_name, scenario)

    logger.info(db.get_collection_document_names(env.cst_scenarios))
    logger.info(db.get_collection_document_names(env.cst_federations))
    logger.info(db.get_dict_key_names(env.cst_federations, federate_name))
    logger.info(db.get_dict(env.cst_federations, None, federate_name))


if __name__ == "__main__":
    mytest1()
    mytest2()
