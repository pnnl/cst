"""
Prototype metadata database API development

@author Trevor Hardy
@date 2023-11-30
"""
import pymongo
from pymongo import MongoClient
import gridfs
import pprint
import logging

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, )

class MetaDB:
    """
    """
    _cu_dict_name = 'cu_metadB_dok'

    def __init__(self, uri_string=None):
        client = None
        collections = []
        db = None
        file_collection_name = "cu_file_collection"
        fs = None 
        

        if uri_string is not None:
            self.client = self._connect_to_database(uri_string)
        else:
            self.client = self._connect_to_database()

        self.db = self.client.metadataDB
        self.fs = gridfs.GridFS(self.db)

        return client       

    def _open_file(file_path, type='r'):
        """
        Utilty function to open file with reasonable error handling.
        """
        try:
            fh = open(file_path, type)
        except IOError:
            logger.error('Unable to open {}'.format(file_path))
        else:
            return fh

    def _connect_to_database(self, uri_string=None):
        """
        Sets up connection to server port for mongodb
        """
        # Set up default uri_string to the server Trevor was using on the EIOC
        if uri_string == None:
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
        for doc in self.db[collection_name].find({}):
            if doc[self._cu_dict_name] == new_name:
                return False 
            else:
                pass  

        return True

    def remove_collection(self, collection_name):
        self.db[collection_name].drop()


    def remove_document(self, collection_name, object_id = None, dict_name = None):
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            self.db[collection_name].delete_one({"_id": object_id})
            self.db[collection_name].delete_one({"_id": object_id})
            raise UserWarning("Using provided object ID (and not provided name) to remove document.")
        elif dict_name is not None:
            doc = self.db[collection_name].delete_one({self._cu_dict_name: dict_name})
            doc = self.db[collection_name].delete_one({self._cu_dict_name: dict_name})
            if not doc:
                raise NameError(f"{dict_name} does not exist in collection {collection_name} and cannot be retrieved.")
        elif object_id is not None:
            self.db[collection_name].delete_one({"_id": object_id})
        # TODO: Add check for success on delete.
        


    def add_collection(self, name):
        """
        Collections don't really exist in MongoDB until at least one document
        has been added to the collection. This method adds a small identifier
        JSON to fill this role.
        """
        id_dict = {"collection name": name,
                   self._cu_dict_name: "collection name"}
        self.db[name].insert_one(id_dict)
        self.collections = self.db.list_collection_names()
        id_dict = {"collection name": name,
                   self._cu_dict_name: "collection name"}
        self.db[name].insert_one(id_dict)
        self.collections = self.db.list_collection_names()

        return name


    def update_collection_names(self):
        """
        Updates the list of collection names in the db object from the 
        database. As you can see in the code below, this is pure syntax
        sugar.
        """
        self.collections = self.db.list_collection_names()

        return self.collections


    def get_collection_document_names(self, collection):
        """
        """
        doc_names = []
        for doc in self.db[collection].find({}):
            doc_names.append(doc[self._cu_dict_name])
        for doc in self.db[collection].find({}):
            doc_names.append(doc[self._cu_dict_name])

        return doc_names


    def get_dict_key_names(self, collection_name, doc_name):
        """
        """
        doc = self.db[collection_name].find({self._cu_dict_name: doc_name})


    def add_dict(self, collection_name, dict_name, dict_to_add):
        """
        Adds the Python dictionary to the specified MongoDB collection as a.
        MongoDB document. Checks to make sure another document does not exist
        by that name; if it does, throw an error.
        
        To allow later access to the document by name, 
        the field "cu_metadB_dok" is added to the dictionary before addding
        it to the collection (the assumption is that "cu_metadB_dok" will 
        always be a unqiue field in the dictionary). 
        """
        if self._check_unique_doc_name(collection_name, dict_name):
        if self._check_unique_doc_name(collection_name, dict_name):
            dict_to_add[self._cu_dict_name] = dict_name
        else:
            raise NameError(f"{dict_name} is not unqiue in collection {collection_name} and cannot be added.")
        obj_id = self.db[collection_name].insert_one(dict_to_add).inserted_id
        
        return str(obj_id)


    def get_dict(self, collection_name, object_id = None, dict_name = None):
        """
        Returns the dictionary in the database based on the user-provided
        object ID or name.

        User must enter either the dictionary name used or the object_ID that
        was created when the dictionary was added but not both.
        """
        if dict_name is None and object_id is None:
            raise AttributeError("Must provide the name or object ID of the dictionary to be retrieved.")
        elif dict_name is not None and object_id is not None:
            doc = self.db[collection_name].find_one({"_id": object_id})
            doc = self.db[collection_name].find_one({"_id": object_id})
            raise UserWarning("Using provided object ID (and not provided name) to to get dictionary.")
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

        return doc


    def update_dict(self, collection_name, updated_dict, object_id = None, dict_name = None):
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
            doc = self.db[collection_name].replace({"_id": object_id}, updated_dict)
            raise UserWarning("Using provided object ID (and not provided name) to update database.")
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
    

if __name__ == "__main__":
    """ 
    Main method for launching meta data class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community: 
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container: 
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
    """
    local_default_uri = 'mongodb://localhost:27017'
    uri = local_default_uri
    metadb = MetaDB(uri_string=uri)




