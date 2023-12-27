"""
Prototype metadata database API development

@author Trevor Hardy
@date 2023-11-30
"""
import os
import pprint
import logging
import subprocess
from pymongo import MongoClient

import helics_messages as hm

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, )

cu_uri = 'mongodb://gage:27017'
cu_database = "copper"
cu_federations = "federations"
cu_scenarios = "scenarios"
cu_logger = "cu_logger"


def federation_database(clear: bool = False):
    db = MetaDB(cu_uri, cu_database)
    print("Before: ",  db.update_collection_names())
    if clear:
        db.db[cu_federations].drop()
        db.db[cu_scenarios].drop()
    db.add_collection(cu_scenarios)
    db.add_collection(cu_federations)
    print("After clear: ", db.update_collection_names())


class MetaDB:
    """
    """
    _cu_dict_name = 'cu_007'

    def __init__(self, uri: str = None, name: str = None):
        self.collections = None

        if uri is not None:
            self.client = self._connect_to_database(uri)
        else:
            self.client = self._connect_to_database()

        if name is not None:
            self.db = self.client[name]
        else:
            self.db = self.client["meta_db"]
        print("Databases: ", self.client.list_database_names())

        # self.fs = gridfs.GridFS(self.db)

    def _open_file(self, file_path, mode='r'):
        """
        Utility function to open file with reasonable error handling.
        """
        try:
            fh = open(file_path, mode)
        except IOError:
            logger.error('Unable to open {}'.format(file_path))
        else:
            return fh

    def _connect_to_database(self, uri_string=None):
        """
        Sets up connection to server port for mongodb
        """
        # Set up default uri_string to the server Trevor was using on the EIOC
        if uri_string is None:
            uri_string = "mongodb://127.0.0.1:27017"
        # Set up connection
        client = MongoClient(uri_string)
        # Test connection
        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
        
        return client

    def _check_unique_doc_name(self, collection_name, new_name):
        """
        Checks to see if the provided document name is unique in the specified
        collection.

        Doesn't throw an error if the name is not unique and let's the calling
        method decide what to do with it.
        """
        for doc in self.db[collection_name].d.find({}, {"_id": 0, self._cu_dict_name: 1}):
            if doc[self._cu_dict_name] == new_name:
                return False 
            else:
                pass  

        return True

    def remove_collection(self, collection_name):
        self.db[collection_name].drop()

    def remove_document(self, collection_name, object_id=None, dict_name=None):
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            # raise UserWarning("Using provided object ID (and not provided name) to remove document.")
            self.db[collection_name].delete_one({"_id": object_id})
        elif dict_name is not None:
            self.db[collection_name].delete_one({self._cu_dict_name: dict_name})
            # if not doc:
            #     raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be retrieved.")
        elif object_id is not None:
            self.db[collection_name].delete_one({"_id": object_id})
        # TODO: Add check for success on delete.

    def add_collection(self, name):
        """
        Collections don't really exist in MongoDB until at least one document
        has been added to the collection. This method adds a small identifier
        JSON to fill this role.
        """
        id_dict = {"collection name": name}
        collection = self.db[name]
        collection.insert_one(id_dict)
        return collection

    def update_collection_names(self):
        """
        Updates the list of collection names in the db object from the database.
        As you can see in the code below, this is pure syntax sugar.
        """
        self.collections = self.db.list_collection_names()
        return self.collections

    def get_collection_document_names(self, collection):
        """
        """
        doc_names = []
        for doc in (self.db[collection].find({}, {"_id": 0, self._cu_dict_name: 1})):
            if doc.__len__():
                doc_names.append(doc[self._cu_dict_name])

        return doc_names

    def get_dict_key_names(self, collection_name, doc_name):
        """
        """
        doc = self.db[collection_name].find({self._cu_dict_name: doc_name})
        return doc[0].keys()

    def add_dict(self, collection_name, dict_name, dict_to_add):
        """
        Adds the Python dictionary to the specified MongoDB collection as a
        MongoDB document. Checks to make sure another document does not exist
        by that name; if it does, throw an error.
        
        To allow later access to the document by name, 
        the field "cu_007" is added to the dictionary before adding
        it to the collection (the assumption is that "cu_007" will
        always be a unique field in the dictionary).
        """
        if self._check_unique_doc_name(collection_name, dict_name):
            dict_to_add[self._cu_dict_name] = dict_name
        else:
            raise NameError(f"{dict_name} is not unique in collection {collection_name} and cannot be added.")

        obj_id = self.db[collection_name].insert_one(dict_to_add).inserted_id
        
        return str(obj_id)

    def get_dict(self, collection_name, object_id=None, dict_name=None):
        """
        Returns the dictionary in the database based on the user-provided
        object ID or name.

        User must enter either the dictionary name used or the object_ID that
        was created when the dictionary was added but not both.
        """
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            # raise UserWarning("Using provided object ID (and not provided name) to get dictionary.")
            doc = self.db[collection_name].find_one({"_id": object_id})
        elif dict_name is not None:
            doc = self.db[collection_name].find_one({self._cu_dict_name: dict_name})
            doc = self.db[collection_name].find_one({self._cu_dict_name: dict_name})
            if not doc:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be retrieved.")
        elif object_id is not None:
            doc = self.db[collection_name].find_one({"_id": object_id})
        # Pulling out the metaDB secret name field that was added when we put
        #   the dictionary into the database. Will not raise an error if 
        #   somehow that key does not exist in the dictionary
        doc.pop(self._cu_dict_name, None)
        doc.pop("_id", None)

        return doc

    def update_dict(self, collection_name, updated_dict, object_id=None, dict_name=None):
        """
        Updates the dictionary on the database (under the same object_ID/name)
        with the passed in updated dictionary.
        
        User must enter either the dictionary name used or the object_ID that
        was created when the dictionary was added but not both.
        """
        updated_dict[self._cu_dict_name] = dict_name
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be modified.")
        elif dict_name is not None and object_id is not None:
            # raise UserWarning("Using provided object ID (and not provided name) to update database.")
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)
        elif dict_name is not None:
            doc = self.db[collection_name].find_one({self._cu_dict_name: dict_name})
            doc = self.db[collection_name].find_one({self._cu_dict_name: dict_name})
            if doc:
                doc = self.db[collection_name].replace({self._cu_dict_name: dict_name}, updated_dict)
            else:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be updated.")
        elif object_id is not None:
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)

        return str(doc["_id"])


def docker_service(name, image, env, cnt, depends=None):
    _service = "  " + name + ":\n"
    _service += "    image: \"" + image + "\"\n"
    if env[0] != '':
        _service += "    environment:\n"
        _service += env[0]
    _service += "    working_dir: /home/worker/case\n"
    _service += "    volumes:\n"
    _service += "      - .:/home/worker/case\n"
    _service += "      - ../../../data:/home/worker/tesp/data\n"
    if depends is not None:
        _service += "    depends_on:\n"
        _service += "      - " + depends + "\n"
    _service += "    networks:\n"
    _service += "      cu_net:\n"
    _service += "        ipv4_address: 10.5.0." + str(cnt) + "\n"
    _service += "    command: sh -c \"" + env[1] + "\"\n"
    return _service


def docker_network():
    _network = 'networks:\n'
    _network += '  cu_net:\n'
    _network += '    driver: bridge\n'
    _network += '    ipam:\n'
    _network += '      config:\n'
    _network += '        - subnet: 10.5.0.0/16\n'
    _network += '          gateway: 10.5.0.1\n'
    return _network

def logger():
    pass

def define_yaml(scenario_name):
    mdb = MetaDB(cu_uri, cu_database)

    scenario_def = mdb.get_dict(cu_scenarios, None, scenario_name)
    federation_name = scenario_def["federation"]
    fed_def = mdb.get_dict(cu_federations, None, federation_name)["federation"]

    yaml = 'version: "3.8"\n'
    yaml += 'services:\n'
    # Add helics broker federate
    cnt = 2
    fed_cnt = str(fed_def.__len__() + 1)
    env = ["", "exec helics_broker --ipv4 -f " + fed_cnt + " --loglevel=warning --name=broker > broker.log"]
    yaml += docker_service("helics", "tesp-helics:latest", env, cnt, depends=None)

    for name in fed_def:
        cnt += 1
        image = fed_def[name]['image']
        env = ["", fed_def[name]['command'] + " > " + name + ".log"]
        yaml += docker_service(name, image, env, cnt, depends=None)

    # Add data logger federate
    cnt += 1
    env = ["", "exec python3 data_logger.py " + scenario_name + " > " + cu_logger + ".log"]
    yaml += docker_service(cu_logger, "tesp-helics:latest", env, cnt, depends=None)

    yaml += docker_network()
    op = open(scenario_name + ".yaml", 'w')
    op.write(yaml)
    op.close()


def run_yaml(scenario_name):
    print('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd(), flush=True)
    docker_compose = "docker-compose -f " + scenario_name + ".yaml"
    subprocess.Popen(docker_compose + " up", shell=True).wait()
    subprocess.Popen(docker_compose + " down", shell=True).wait()
    print('====  Broker Exit in\n        ' + os.getcwd(), flush=True)


def scenario_tojson(federation: str, start: str, stop: str):
    return {
        "federation": federation,
        "start_time": start,
        "stop_time": stop
    }


def mytest1():
    """
    Main method for launching meta data class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community: 
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container: 
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = MetaDB(cu_uri, cu_database)
    print(db.update_collection_names())
    scenarios = db.add_collection(cu_scenarios)
    federates = db.add_collection(cu_federations)

    t1 = hm.HelicsMsg("Battery", 30)
    t1.config("core_type", "zmq")
    t1.config("log_level", "warning")
    t1.config("period", 60)
    t1.config("uninterruptible", False)
    t1.config("terminate_on_error", True)
    t1.config("wait_for_current_time_update", True)
    t1.pubs_e(True, "Battery/EV1_current", "double", "A")
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
    federate_name = "BT1"
    db.add_dict(cu_federations, federate_name, diction)

    scenario = scenario_tojson(federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(cu_scenarios, scenario_name, scenario)

    print(db.get_collection_document_names(cu_scenarios))
    print(db.get_collection_document_names(cu_federations))
    print(db.get_dict_key_names(cu_federations, federate_name))
    print(db.get_dict(cu_federations, None, federate_name))


def mytest2():
    """
    Main method for launching meta data class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community:
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container:
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = MetaDB(cu_uri, cu_database)
    print(db.update_collection_names())
    db.add_collection(cu_scenarios)
    db.add_collection(cu_federations)

    t1 = hm.HelicsMsg("Battery", 30)
    t1.config("core_type", "zmq")
    t1.config("log_level", "warning")
    t1.config("period", 60)
    t1.config("uninterruptible", False)
    t1.config("terminate_on_error", True)
    t1.config("wait_for_current_time_update", True)
    t1.pubs_e(True, "Battery/EV1_current", "double", "A")
    t1.subs_e(True, "EVehicle/EV1_voltage", "double", "V")
    t1 = {
        "image": "python/3.11.7-slim-bullseye",
        "federate_type": "value",
        "time_step": 120,
        "HELICS_config": t1.write_json()
    }

    t2 = hm.HelicsMsg("EVehicle", 30)
    t2.config("core_type", "zmq")
    t2.config("log_level", "warning")
    t2.config("period", 60)
    t2.config("uninterruptible", False)
    t2.config("terminate_on_error", True)
    t2.config("wait_for_current_time_update", True)
    t2.subs_e(True, "Battery/EV1_current", "double", "A")
    t2.pubs_e(True, "EVehicle/EV1_voltage", "double", "V")
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
    federate_name = "BT1"
    db.add_dict(cu_federations, federate_name, diction)

    scenario = scenario_tojson(federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(cu_scenarios, scenario_name, scenario)

    scenario_name = "TE100"
    # seems to remember the scenario address, not the value so reinitialize
    scenario = scenario_tojson(federate_name, "2023-12-07T15:31:27", "2023-12-10T15:31:27")
    db.add_dict(cu_scenarios, scenario_name, scenario)

    print(db.get_collection_document_names(cu_scenarios))
    print(db.get_collection_document_names(cu_federations))
    print(db.get_dict_key_names(cu_federations, federate_name))
    print(db.get_dict(cu_federations, None, federate_name))


federation_database()


if __name__ == "__main__":
    mytest1()
