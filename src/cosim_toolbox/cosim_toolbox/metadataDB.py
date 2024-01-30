"""
Prototype metadata database API development

@author Trevor Hardy
@date 2023-11-30
"""
import os
import pprint
import logging
import subprocess
import gridfs
from pymongo import MongoClient

import cosim_toolbox.helics_config as hm

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, )

sim_user = os.environ.get("SIM_USER", "worker")
sim_host = os.environ.get("SIM_HOST", "localhost")

cosim_mongo_host = os.environ.get("MONGO_HOST", "mongodb://localhost:27017")
cosim_mongo_db = os.environ.get("COSIM_DB", "copper")

cu_federations = "federations"
cu_scenarios = "scenarios"
cu_logger = "cu_logger"


def federation_database(clear: bool = False):
    db = MetaDB(cosim_mongo_host, cosim_mongo_db)
    logger.info("Before: ",  db.update_collection_names())
    if clear:
        db.db[cu_federations].drop()
        db.db[cu_scenarios].drop()
    db.add_collection(cu_scenarios)
    db.add_collection(cu_federations)
    logger.info("After clear: ", db.update_collection_names())


class MetaDB:
    """
    """
    _cu_dict_name = 'cu_007'

    def __init__(self, uri=None, db_name=None):
        self.collections = None

        self.client = self._connect_to_database(uri, db_name)

        if db_name is not None:
            self.db = self.client[db_name]
        else:
            self.db = self.client["meta_db"]
        self.fs = gridfs.GridFS(self.db)

    @staticmethod
    def _open_file(file_path, mode='r'):
        """
        Utility function to open file with reasonable error handling.
        """
        try:
            fh = open(file_path, mode)
        except IOError:
            logger.error('Unable to open {}'.format(file_path))
        else:
            return fh

    @staticmethod
    def _connect_to_database(uri=None, db=None):
        """
        Sets up connection to server port for mongodb
        """
        cosim_user = os.environ.get("COSIM_USER", "worker")
        cosim_password = os.environ.get("COSIM_PASSWORD", "worker")

        # Set up default uri_string to the server Trevor was using on the EIOC
        if uri is None:
            uri = cosim_mongo_host
        if db is None:
            db = cosim_mongo_db
        # Set up connection
        uri = uri.replace('//', '//' + cosim_user + ':' + cosim_password + '@')
        client = MongoClient(uri + '/?authSource=' + db + '&authMechanism=SCRAM-SHA-1')
        # Test connection
        try:
            client.admin.command('ping')
            logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            logger.info(e)

        return client

    def _check_unique_doc_name(self, collection_name, new_name):
        """
        Checks to see if the provided document name is unique in the specified
        collection.

        Doesn't throw an error if the name is not unique and lets the calling
        method decide what to do with it.
        """
        ret_val = True
        for doc in (self.db[collection_name].find({self._cu_dict_name: 1})):
            if doc[self._cu_dict_name] == new_name:
                ret_val = False
        return ret_val

    def add_file(self, file, conflict='fail', name=None):
        """
        Gets file from disk and adds it to the metadataDB for all federates
        to use.

        The "name" parameter is optional. If provided, the file will be
        stored by that name in the database. If omitted, the name of the
        file itself will be used.

        MongoDB allows files to have the same name and creates unique IDs.
        By default, this method will produce an error if the name of the
        file being added already exists in the file storage. This can
        behavior can be altered by specifying the "conflict" parameter
        to a different value.
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

    def get_file(self, name, disk_name=None, path=None):
        """
        Pulls a file from the metadataDB by name and optionally writes it to
        disk. This method only gets the latest version of the file (if
        multiple versions exist).

        If "disk_name" is specified, that name will be used when writing the
        file to disk; otherwise the file name as specified in the metadataDB
        will be used. If path is not specified, the file is not written to
        disk. If it is the file is written at the location specified by path
        using the provided "disk_name".
        """
        db_file = self.fs.files.find({'filename': name})
        if not db_file:
            raise NameError(f"File '{name}' does not exist.")
        else:
            db_file = self.fs.get_last_version(filename=name)
            if path:
                if disk_name:
                    path = os.path.join(path, disk_name)
                else:
                    path = os.path.join(path, name)
                fh = self._open_file(path, 'wb')
                fh.write(db_file)
            else:
                return db_file

    def remove_collection(self, collection_name):
        self.db[collection_name].drop()

    def remove_document(self, collection_name, object_id=None, dict_name=None):
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            logger.warning("Using provided object ID (and not provided name) to remove document.")
            self.db[collection_name].delete_one({"_id": object_id})
        elif dict_name is not None:
            self.db[collection_name].delete_one({self._cu_dict_name: dict_name})
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
        for doc in (self.db[collection].find({"_id": 0, self._cu_dict_name: 1})):
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
            logger.warning("Using provided object ID (and not provided name) to get dictionary.")
            doc = self.db[collection_name].find_one({"_id": object_id})
        elif dict_name is not None:
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
            logger.warning("Using provided object ID (and not provided name) to update database.")
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)
        elif dict_name is not None:
            doc = self.db[collection_name].find_one({self._cu_dict_name: dict_name})
            if doc:
                doc = self.db[collection_name].replace({self._cu_dict_name: dict_name}, updated_dict)
            else:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be updated.")
        elif object_id is not None:
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)

        return str(doc["_id"])

    @staticmethod
    def scenario(schema_name: str, federation_name: str, start: str, stop: str, docker: bool = False):
        return {
            "schema": schema_name,
            "federation": federation_name,
            "start_time": start,
            "stop_time": stop,
            "docker": docker
        }


class Docker:
    def __init__(self):
        pass

    @staticmethod
    def _service(name, image, env, cnt, depends=None):
        _service = "  " + name + ":\n"
        _service += "    image: \"" + image + "\"\n"
        if env[0] != '':
            _service += "    environment:\n"
            _service += env[0]
        _service += "    user: worker\n"
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
        _service += "    command: /bin/bash -c \"" + env[1] + "\"\n"
        return _service

    @staticmethod
    def _network():
        _network = 'networks:\n'
        _network += '  cu_net:\n'
        _network += '    driver: bridge\n'
        _network += '    ipam:\n'
        _network += '      config:\n'
        _network += '        - subnet: 10.5.0.0/16\n'
        _network += '          gateway: 10.5.0.1\n'
        return _network

    @staticmethod
    def define_yaml(scenario_name):
        mdb = MetaDB(cosim_mongo_host, cosim_mongo_db)

        scenario_def = mdb.get_dict(cu_scenarios, None, scenario_name)
        federation_name = scenario_def["federation"]
        schema_name = scenario_def["schema"]
        fed_def = mdb.get_dict(cu_federations, None, federation_name)["federation"]

        yaml = 'version: "3.8"\n'
        yaml += 'services:\n'
        # Add helics broker federate
        cnt = 2
        fed_cnt = str(fed_def.__len__() + 1)
        env = ["", "exec helics_broker --ipv4 -f " + fed_cnt + " --loglevel=warning --name=broker"]
        yaml += Docker._service("helics", "cosim-helics:latest", env, cnt, depends=None)

        for name in fed_def:
            cnt += 1
            image = fed_def[name]['image']
            env = ["", fed_def[name]['command']]
            yaml += Docker._service(name, image, env, cnt, depends=None)

        # Add data logger federate
        cnt += 1
        env = ["", "source /home/worker/venv/bin/activate && exec python3 -c \\\"import cosim_toolbox.data_logger as datalog; datalog.main('DataLogger', '" +
               schema_name + "', '" + scenario_name + "')\\\""]
        yaml += Docker._service(cu_logger, "cosim-python:latest", env, cnt, depends=None)

        yaml += Docker._network()
        op = open(scenario_name + ".yaml", 'w')
        op.write(yaml)
        op.close()

    @staticmethod
    def run_yaml(scenario_name):
        logger.info('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd())
        docker_compose = "docker-compose -f " + scenario_name + ".yaml"
        subprocess.Popen(docker_compose + " up", shell=True).wait()
        subprocess.Popen(docker_compose + " down", shell=True).wait()
        logger.info('====  Broker Exit in\n        ' + os.getcwd())

    @staticmethod
    def run_remote_yaml(scenario_name):
        cosim = os.environ.get("SIM_DIR", "/home/worker/copper")
        logger.info('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd())
        docker_compose = "docker-compose -f " + scenario_name + ".yaml"
        cmd = ("sh -c 'cd " + cosim + "/run/python/test_federation && " +
               docker_compose + " up && " + docker_compose + " down'")
        subprocess.Popen("ssh -i  ~/copper-key-ecdsa " + sim_user + "@" + sim_host +
                         " \"nohup " + cmd + " > /dev/null &\"", shell=True)
        logger.info('====  Broker Exit in\n        ' + os.getcwd())


def mytest1():
    """
    Main method for launching metadata class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community:
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container:
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = MetaDB(cosim_mongo_host, cosim_mongo_db)
    logger.info(db.update_collection_names())
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
    schema_name = "Tesp"
    federate_name = "BT1"
    db.add_dict(cu_federations, federate_name, diction)

    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(cu_scenarios, scenario_name, scenario)

    logger.info(db.get_collection_document_names(cu_scenarios))
    logger.info(db.get_collection_document_names(cu_federations))
    logger.info(db.get_dict_key_names(cu_federations, federate_name))
    logger.info(db.get_dict(cu_federations, None, federate_name))


def mytest2():
    """
    Main method for launching metadata class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community:
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container:
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    db = MetaDB(cosim_mongo_host, cosim_mongo_db)
    logger.info(db.update_collection_names())
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
    schema_name = "Tesp"
    federate_name = "BT1_EV1"
    db.add_dict(cu_federations, federate_name, diction)

    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(cu_scenarios, scenario_name, scenario)

    scenario_name = "TE100"
    # seems to remember the scenario address, not the value so reinitialize
    scenario = db.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-10T15:31:27", True)
    db.add_dict(cu_scenarios, scenario_name, scenario)

    logger.info(db.get_collection_document_names(cu_scenarios))
    logger.info(db.get_collection_document_names(cu_federations))
    logger.info(db.get_dict_key_names(cu_federations, federate_name))
    logger.info(db.get_dict(cu_federations, None, federate_name))


if __name__ == "__main__":
    mytest1()
    mytest2()
