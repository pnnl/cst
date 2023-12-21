"""
Prototype metadata database API development

@author Trevor Hardy
@date 2023-11-30
"""

from pymongo import MongoClient
import gridfs
import pprint
import logging
import helics_messages as hm

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, )


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
            if doc:
                doc = self.db[collection_name].replace({self._cu_dict_name: dict_name}, updated_dict)
            else:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be updated.")
        elif object_id is not None:
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)

        return str(doc["_id"])


def scenarioToJson(federation: str, start: str, stop: str):
    return {
        "federation": federation,
        "start_time": start,
        "stop_time": stop
    }


if __name__ == "__main__":
    """ 
    Main method for launching meta data class
    First user's will need to set up docker desktop, install mongodb community: 
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container: 
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    local_uri = 'mongodb://localhost:27017'
    db_name = "copper"
    fed = "federations"
    scr = "scenarios"
    db = MetaDB(local_uri, db_name)
    db.db[fed].drop()
    db.db[scr].drop()
    scenarios = db.add_collection(scr)
    federates = db.add_collection(fed)

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
    federate_name = "BT1_EV1"
    db.add_dict(fed, federate_name, diction)

    # for x in federates.find({}, {"_id": 0, "cu_name": 1, "federation": 1}):
    for x in federates.find():
        print(x)
#    print(federates.find()[0])
#    print(db.db[federate_name].find()[0])
#    print(db.db[federate_name].find({}, {"_id": 0, "cu_name": 1, "federation": 1}))

    scenario = scenarioToJson(federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
    db.add_dict(scr, scenario_name, scenario)
    scenario_name = "TE100"
    # seems to remember the scenario address, not the value so reinitialize
    scenario = scenarioToJson(federate_name, "2023-12-07T15:31:27", "2023-12-10T15:31:27")
    db.add_dict(scr, scenario_name, scenario)
    # for x in scenarios.find({}, {"_id": 0, "cu_name": 1}):
    for x in scenarios.find():
        print(x)

    print(db.get_collection_document_names(scr))
    print(db.get_collection_document_names(fed))
    print(db.get_dict_key_names(fed, federate_name))
    print(db.get_dict(fed, None, federate_name))
