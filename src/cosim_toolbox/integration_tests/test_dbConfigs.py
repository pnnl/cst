import copy
import json
import os
import unittest

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs

import collections
collections.Callable = collections.abc.Callable

class TestMetadataDBApi(unittest.TestCase):
    fileDictionary = dict()

    update_data = [
        {
            "cst_007": "federation documents"
        },
        {
            "cst_007": "BT1_EV1",
            "federation": {
                "EVehicle": {
                    "federate_type": "value",
                    "time_step": 120,
                }
            }
        },
        {
            "cst_007": "BT2_EV2",
            "federation": {
                "EVehicle": {
                    "federate_type": "value",
                    "time_step": 120,
                }
            }
        }
    ]

    def setUp(self):
        self.metadb = DBConfigs(env.cst_mg_host, env.cst_mongo_db)

    def test_01__open_file(self):
        file_path = os.path.join(os.path.dirname(__file__), "data", "psc_ex.json")
        self.assertTrue(os.path.exists(file_path))
        file = None
        try:
            file = self.metadb._open_file(file_path)
        except:
            self.assertIsNone(file, "Error opening file")
        file_dict = None
        try:
            file_dict = json.load(file)
        except json.JSONDecodeError as e:
            self.assertTrue(False, "Error loading JSON file")
        named_file_dict = {"psc": file_dict}
        self.assertEqual(len(named_file_dict), 1, "Unable to correctly load file_dict")
        file.close()
        pass

    def test_02_add_collection(self):
        collection_name = "case_data"
        name_list = ["case_data"]
        name_out = self.metadb.add_collection(name=collection_name)
        name_collections = self.metadb.update_collection_names()
        section = list(set(name_list).intersection(name_collections))
        self.assertEqual(len(section), 1, "return collection did not contain new collection name")

    def test_03_remove_collection(self):
        dict_name = "psc3"
        collection_name = "case_data3"
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc3': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        name_collections = self.metadb.update_collection_names()
        for c in name_collections:
            self.metadb.remove_collection(c)
        self.assertEqual(len(self.metadb.collections), 0, "not all collections were removed")

    def test_04_add_dict(self):
        dict_name = "psc4"
        collection_name = "case_data4"
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc4': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        self.assertIsNot(obj_id, "", "add_dict failed")

    def test_05_get_dict_key_names(self):
        dict_name = "psc5"
        collection_name = "case_data5"
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc5': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        keys = self.metadb.get_dict_key_names(collection_name, dict_name)
        self.assertTrue(len(keys) > 0, "no key names were returned")

    def test_06_check_unique_doc_name(self):
        collection_name = "case_data"
        dict_name = "psc"
        file_name_unique = self.metadb._check_unique_doc_name(collection_name, dict_name)
        self.assertTrue(file_name_unique, "unique check incorrectly returned False")
        dict_name = "psc6"
        collection_name = "case_data6"
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc6': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        file_name_unique = self.metadb._check_unique_doc_name(collection_name, dict_name)
        self.assertFalse(file_name_unique, "unique check incorrectly returned True")

    def test_07_update_collection_names(self):
        dict_name = "psc7"
        collection_name = "case_data7"
        name_out = self.metadb.add_collection(name=collection_name)
        name_collections = self.metadb.update_collection_names()
        self.assertTrue(len(name_collections) > 0, "no collection names were returned")

    def test_08_get_collection_document_names(self):
        dict_name = "psc8"
        collection_name = "case_data8"
        name_out = self.metadb.add_collection(name=collection_name)

        named_file_dict = {'psc8': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)

        doc_names = self.metadb.get_collection_document_names(collection_name)
        self.assertTrue(len(doc_names) > 0, "no document names were returned")

    def test_09_remove_document(self):
        dict_name = "psc9"
        collection_name = "case_data9"
        name_list = ["case_data9"]
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc9': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                    'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                    'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                    'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        try:
            doc_names = self.metadb.get_collection_document_names(collection_name)
            self.metadb.remove_document(collection_name=collection_name, dict_name="psc9")
            doc_names2 = self.metadb.get_collection_document_names(collection_name)
            name_collections = self.metadb.update_collection_names()
            section = list(set(name_list).intersection(name_collections))
            self.assertNotEqual(doc_names, doc_names2)
        except AttributeError as e:
            print("AttributeError : ", e)
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        try:
            doc_names = self.metadb.get_collection_document_names(collection_name)
            self.metadb.remove_document(collection_name=collection_name, dict_name="blah")
            doc_names2 = self.metadb.get_collection_document_names(collection_name)
            self.assertEqual(doc_names, doc_names2, "invalid dict_name entered")
        except NameError as e:
            print("NameError : ", e)
            self.assertNotEqual(1, 0, "invalid dict_name entered")

    def test_10_get_dict(self):
        dict_name = "psc10"
        collection_name = "case_data10"
        name_out = self.metadb.add_collection(name=collection_name)
        named_file_dict = {'psc10': {'bus': {'bus_num': [1, 2, 3, 4, 5]},
                                     'branch': {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                                     'gen': {'bus_num': [1, 2, 3], 'id': ['1', '1', '1'], 'mw': [10, 20, 30]},
                                     'load': {'bus_num': [4, 5, 5], 'id': ['1', '1', '2'], 'mw': [12, 17, 25]}}}
        obj_id = self.metadb.add_dict(collection_name, dict_name, named_file_dict)
        dict_obj = self.metadb.get_dict(collection_name=collection_name, dict_name=dict_name)
        self.assertGreater(len(dict_obj['psc10']['branch']), 0, "dict_obj['psc10']['branch'] has zero length")
        self.assertEqual(dict_obj['psc10']['branch'], {'from_bus': [1, 1, 1, 3, 4], 'to_bus': [2, 3, 5, 2, 5]},
                         "[psc10]['branch'] elements do not match")

    def test_11_update_dict(self):
        collection_name = "case_data11"
        dict_name = self.update_data[1]['cst_007']
        name_out = self.metadb.add_collection(name=collection_name)
        copy_dict = copy.deepcopy(self.update_data[1]['federation'])
        obj_id = self.metadb.add_dict(collection_name, dict_name, copy_dict)
        dict_obj = self.metadb.get_dict(collection_name=collection_name, dict_name=dict_name)
        dict_obj["EVehicle"]["time_step"] -= 60
        # print(self.metadb.get_collection_document_names(collection_name), flush=True)
        test_result = self.metadb.update_dict(collection_name=collection_name, updated_dict=dict_obj,
                                              dict_name=dict_name)
        new_dict_obj = self.metadb.get_dict(collection_name=collection_name, dict_name=dict_name)
        # print(self.metadb.get_collection_document_names(collection_name), flush=True)
        self.assertNotEqual(new_dict_obj, dict_obj)
        self.assertEqual(copy_dict["EVehicle"]["time_step"] - 60, new_dict_obj["EVehicle"]["time_step"])

    def test_12_scenario(self):
        schema_name = "Tesp"
        federate_name = "BT1"
        scenario = self.metadb.scenario(schema_name, federate_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
        self.assertEqual(scenario['federation'], 'BT1', "scenario federation value is not set correctly")

    def tearDown(self):
        self.metadb = None


if __name__ == '__main__':
    unittest.main()
