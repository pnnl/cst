from metadataDB import MetaDB

""" 
    Main method for launching meta data class to ping local container of mongodb.
    First user's will need to set up docker desktop (through the PNNL App Store), install mongodb community: 
    https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/
    But run docker with the port number exposed to the host so that it can be pinged from outside the container: 
    docker run --name mongodb -d -p 27017:27017 mongodb/mongodb-community-server:$MONGODB_VERSION
    If no version number is important the tag MONGODB_VERSION=latest can be used
"""


local_default_uri = 'mongodb://localhost:27017'
metadb = MetaDB(uri=local_default_uri)

# test adding a data collection
name = "copper_data"
name_out = metadb.add_collection(name=name)

# test adding a document
collection_name = "copper_data"
dict_name = "psc"
dict_to_add = {
    "bus": {
        "bus_num": [1, 2 ,3, 4, 5],
    },
    "branch": {
        "from_bus": [1, 1, 1, 3, 4],
        "to_bus": [2, 3, 5, 2, 5]
    },
    "gen": {
        "bus_num": [1, 2, 3],
        "id": ["1", "1", "1"],
        "mw": [10, 20, 30]
    },
    "load": {
        "bus_num": [4, 5, 5],
        "id": ["1", "1", "2"],
        "mw": [12, 17, 25]
    }
}
obj_id = metadb.add_dict(collection_name, dict_name, dict_to_add)

# test update_collection_name(self)
collections = metadb.update_collection_names()
print("Collection_names = ", collections)

# test get_collection_document_names(self, collection)
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names = ", doc_names)

# test remove_document(self, collection_name, object_id = None, dict_name = None):
#first test error catching
try:
    metadb.remove_document(collection_name)
except AttributeError as e:
    print("AttributeError : ", e)

try:
    metadb.remove_document(collection_name, dict_name = 'blah')
except NameError as e:
    print("NameError : ", e) 

# now test works
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names before: ", doc_names)
metadb.remove_document(collection_name, dict_name = dict_name)
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names after: ", doc_names)

# test removing a data collection
name = "copper_data"
metadb.remove_collection(name)