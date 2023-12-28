from metadataDB import MetaDB

import os
import json

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

# Testing methods in metadataDB.py

# test removing a data collection
collections = metadb.update_collection_names()
for c in collections:
    metadb.remove_collection(c)

# test adding a data collection
collection_name = "case_data"
name_out = metadb.add_collection(name=collection_name)
collections = metadb.update_collection_names()
print(collections)

# test _open_file(self, file_path, mode='r'):
file_path = os.path.join(os.path.dirname(__file__), "data", "psc_ex.json")
print(file_path)
file = metadb._open_file(file_path)
file_dict = json.load(file)
named_file_dict = {"psc": file_dict}

# test adding a document
dict_name = "psc"
obj_id = metadb.add_dict(collection_name, dict_name, named_file_dict)

#test get get_dict_key_names(self, collection_name, doc_name):
keys = metadb.get_dict_key_names(collection_name, dict_name)
print(f"Dictionary keys of {dict_name}: {keys}")

# test _check_unique_doc_name(self, collection_name, new_name):
file_name_unique = metadb._check_unique_doc_name(collection_name, dict_name)
print("File name unique? ", file_name_unique)

# test update_collection_name(self)
collections = metadb.update_collection_names()
print("Collection_names = ", collections)

# test get_collection_document_names(self, collection)
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names = ", doc_names)

# test remove_document(self, collection_name, object_id = None, dict_name = None):
# first test error catching
try:
    metadb.remove_document(collection_name)
except AttributeError as e:
    print("AttributeError : ", e)

try:
    metadb.remove_document(collection_name, dict_name='blah')
except NameError as e:
    print("NameError : ", e) 

# now test works
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names before: ", doc_names)
metadb.remove_document(collection_name, dict_name=dict_name)
doc_names = metadb.get_collection_document_names(collection_name)
print("Doc names after: ", doc_names)

# test removing a data collection
metadb.remove_collection(collection_name)