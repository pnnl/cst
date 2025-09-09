"""
Test script for JSON metadata management implementation.
"""

import tempfile
import shutil
from pathlib import Path

# Add the source path so we can import our modules
import sys
sys.path.insert(0, 'src/cosim_toolbox')

from cosim_toolbox.dbms import TSRecord
from cosim_toolbox.dbms import JSONMetadataManager


def test_basic_functionality():
    """Test basic JSON metadata manager functionality."""
    
    print("=== Testing Basic JSON Metadata Manager ===")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Testing in directory: {temp_dir}")
    
    try:
        # Test with context manager
        with JSONMetadataManager(temp_dir) as manager:
            print(f"Connected: {manager.is_connected}")
            
            # Test federation write/read
            print("\n--- Testing Federation Management ---")
            fed_data = {
                "federation": {
                    "Battery": {
                        "image": "cosim-cst:latest",
                        "command": "python3 simple_federate.py Battery MyScenario",
                        "federate_type": "value",
                        "time_step": 120,
                        "HELICS_config": {
                            "name": "Battery",
                            "core_type": "zmq",
                            "log_level": "warning",
                            "period": 60,
                            "uninterruptible": False,
                            "terminate_on_error": True,
                            "wait_for_current_time_update": True,
                            "publications": [
                                {
                                    "global": True,
                                    "key": "Battery/EV1_current",
                                    "type": "double",
                                    "unit": "A"
                                }
                            ],
                            "subscriptions": [
                                {
                                    "global": True,
                                    "key": "EVehicle/EV1_voltage",
                                    "type": "double",
                                    "unit": "V"
                                }
                            ]
                        }
                    },
                    "EVehicle": {
                        "image": "cosim-cst:latest",
                        "command": "python3 simple_federate.py EVehicle MyScenario",
                        "federate_type": "value",
                        "time_step": 120,
                        "HELICS_config": {
                            "name": "EVehicle",
                            "core_type": "zmq",
                            "log_level": "warning",
                            "period": 60,
                            "uninterruptible": False,
                            "terminate_on_error": True,
                            "wait_for_current_time_update": True,
                            "publications": [
                                {
                                    "global": True,
                                    "key": "EVehicle/EV1_voltage",
                                    "type": "double",
                                    "unit": "V"
                                }
                            ],
                            "subscriptions": [
                                {
                                    "global": True,
                                    "key": "Battery/EV1_current",
                                    "type": "double",
                                    "unit": "A"
                                }
                            ]
                        }
                    }
                }
            }
            
            success = manager.write_federation("MyFederation", fed_data)
            print(f"Federation write: {'✓' if success else '✗'}")
            
            read_fed = manager.read_federation("MyFederation")
            print(f"Federation read: {'✓' if read_fed else '✗'}")
            
            if read_fed:
                print(f"Federation has {len(read_fed['federation'])} federates")
                
            # Test scenario write/read
            print("\n--- Testing Scenario Management ---")
            scenario_data = {
                "analysis": "MyAnalysis",
                "federation": "MyFederation",
                "start_time": "2023-12-07T15:31:27",
                "stop_time": "2023-12-08T15:31:27",
                "docker": False
            }
            
            success = manager.write_scenario("MyScenario", scenario_data)
            print(f"Scenario write: {'✓' if success else '✗'}")
            
            read_scenario = manager.read_scenario("MyScenario")
            print(f"Scenario read: {'✓' if read_scenario else '✗'}")
            
            if read_scenario:
                print(f"Scenario references federation: {read_scenario['federation']}")
            
            # Test custom data
            print("\n--- Testing Custom Data ---")
            custom_data = {
                "test_parameter": 42,
                "test_array": [1, 2, 3],
                "nested_data": {
                    "voltage_range": [110, 130],
                    "frequency": 60
                }
            }
            
            success = manager.write("test_parameters", "electrical_config", custom_data)
            print(f"Custom data write: {'✓' if success else '✗'}")
            
            read_custom = manager.read("test_parameters", "electrical_config")
            print(f"Custom data read: {'✓' if read_custom else '✗'}")
            
            # Test listing
            print("\n--- Testing Listing Functions ---")
            federations = manager.list_federations()
            scenarios = manager.list_scenarios()
            collections = manager.list_custom_collections()
            
            print(f"Listed federations: {federations}")
            print(f"Listed scenarios: {scenarios}")
            print(f"Listed custom collections: {collections}")
            
            if collections:
                items = manager.list_items("test_parameters")
                print(f"Items in 'test_parameters': {items}")
            
            # Test existence checks
            print("\n--- Testing Existence Checks ---")
            print(f"Federation 'MyFederation' exists: {manager.exists_federation('MyFederation')}")
            print(f"Federation 'NonExistent' exists: {manager.exists_federation('NonExistent')}")
            print(f"Scenario 'MyScenario' exists: {manager.exists_scenario('MyScenario')}")
            print(f"Custom data exists: {manager.exists('test_parameters', 'electrical_config')}")
            
            # Test file structure
            print("\n--- Verifying File Structure ---")
            print(f"Base directory exists: {Path(temp_dir).exists()}")
            print(f"Federations directory exists: {(Path(temp_dir) / 'federations').exists()}")
            print(f"Scenarios directory exists: {(Path(temp_dir) / 'scenarios').exists()}")
            print(f"Custom collection directory exists: {(Path(temp_dir) / 'test_parameters').exists()}")
            
            # List actual files created
            for root, dirs, files in Path(temp_dir).walk():
                relative_root = root.relative_to(temp_dir)
                if files:
                    print(f"Files in {relative_root}: {files}")
        
        print("\n--- Testing Error Handling ---")
        # Test operations without connection
        manager = JSONMetadataManager(temp_dir)
        # Don't connect
        result = manager.read_federation("MyFederation")
        print(f"Read without connection (should fail): {'✗' if result is None else '✓'}")
        
        print("\n=== JSON Metadata Manager Test Complete ===")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


def test_with_federation_runner_data():
    """Test using data structure similar to federation runner."""
    
    print("\n=== Testing with Federation Runner Data ===")
    
    temp_dir = tempfile.mkdtemp()
    print(f"Testing federation runner compatibility in: {temp_dir}")
    
    try:
        with JSONMetadataManager(temp_dir) as manager:
            
            # Simulate the federation data that would be created by runner2.py
            federation_data = {
                "federation": {
                    "Battery": {
                        "logger": False,
                        "image": "",
                        "command": "python3 simple_federate.py Battery MyScenario",
                        "federate_type": "value",
                        "HELICS_config": {
                            "name": "Battery",
                            "core_type": "zmq",
                            "log_level": "warning",
                            "period": 60,
                            "uninterruptible": False,
                            "terminate_on_error": True,
                            "wait_for_current_time_update": True,
                            "tags": {"logger": "no"},
                            "publications": [
                                {
                                    "global": True,
                                    "key": "Battery/EV_current",
                                    "type": "double",
                                    "unit": "A"
                                }
                            ],
                            "subscriptions": [
                                {
                                    "key": "EVehicle/EV_voltage",
                                    "type": "double",
                                    "unit": "V"
                                }
                            ]
                        }
                    },
                    "EVehicle": {
                        "logger": False,
                        "image": "",
                        "command": "python3 simple_federate.py EVehicle MyScenario",
                        "federate_type": "value",
                        "HELICS_config": {
                            "name": "EVehicle",
                            "core_type": "zmq",
                            "log_level": "warning",
                            "period": 60,
                            "uninterruptible": False,
                            "terminate_on_error": True,
                            "wait_for_current_time_update": True,
                            "tags": {"logger": "no"},
                            "publications": [
                                {
                                    "global": True,
                                    "key": "EVehicle/EV_voltage",
                                    "type": "double",
                                    "unit": "V"
                                }
                            ],
                            "subscriptions": [
                                {
                                    "key": "Battery/EV_current",
                                    "type": "double",
                                    "unit": "A"
                                }
                            ]
                        }
                    }
                }
            }
            
            scenario_data = {
                "analysis": "MyAnalysis",
                "federation": "MyFederation",
                "start_time": "2023-12-07T15:31:27",
                "stop_time": "2023-12-08T15:31:27",
                "docker": False
            }
            
            # Write the data
            fed_success = manager.write_federation("MyFederation", federation_data)
            scenario_success = manager.write_scenario("MyScenario", scenario_data)
            
            print(f"Federation write: {'✓' if fed_success else '✗'}")
            print(f"Scenario write: {'✓' if scenario_success else '✗'}")
            
            # Read it back and verify structure
            read_federation = manager.read_federation("MyFederation")
            read_scenario = manager.read_scenario("MyScenario")
            
            if read_federation and read_scenario:
                print("✓ Data structure verification:")
                
                # Check federation structure
                federates = read_federation["federation"]
                print(f"  - Found {len(federates)} federates: {list(federates.keys())}")
                
                for fed_name, fed_config in federates.items():
                    helics_config = fed_config["HELICS_config"]
                    pubs = helics_config.get("publications", [])
                    subs = helics_config.get("subscriptions", [])
                    print(f"  - {fed_name}: {len(pubs)} pubs, {len(subs)} subs")
                
                # Check scenario structure  
                print(f"  - Scenario references federation: {read_scenario['federation']}")
                print(f"  - Time range: {read_scenario['start_time']} to {read_scenario['stop_time']}")
                
                # Verify the data can be used like the original DBConfigs
                # This simulates what a federate would do to get its config
                federation_name = read_scenario["federation"]
                federation_config = manager.read_federation(federation_name)
                
                if federation_config:
                    battery_config = federation_config["federation"]["Battery"]
                    battery_helics = battery_config["HELICS_config"]
                    
                    print(f"  - Battery federate type: {battery_config['federate_type']}")
                    print(f"  - Battery period: {battery_helics['period']}")
                    print(f"  - Battery publications: {[p['key'] for p in battery_helics['publications']]}")
                    
                print("✓ Federation runner compatibility verified")
            else:
                print("✗ Failed to read back data")
    
    finally:
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


def test_tsrecord():
    """Test the TSRecord dataclass."""
    
    print("\n=== Testing TSRecord ===")
    
    from datetime import datetime
    
    # Create a sample record
    record = TSRecord(
        real_time=datetime.now(),
        sim_time=120.5,
        scenario="MyScenario",
        federate="Battery",
        data_name="Battery/EV1_current",
        data_value=15.7
    )
    
    print(f"Created TSRecord: {record}")
    print(f"Real time: {record.real_time}")
    print(f"Sim time: {record.sim_time}")
    print(f"Scenario: {record.scenario}")
    print(f"Federate: {record.federate}")
    print(f"Data name: {record.data_name}")
    print(f"Data value: {record.data_value} ({type(record.data_value)})")
    
    # Test with different data types
    records = [
        TSRecord(datetime.now(), 0.0, "test", "fed1", "voltage", 120.5),  # float
        TSRecord(datetime.now(), 1.0, "test", "fed1", "count", 42),      # int
        TSRecord(datetime.now(), 2.0, "test", "fed1", "status", "active"), # string
        TSRecord(datetime.now(), 3.0, "test", "fed1", "flag", True),     # bool
        TSRecord(datetime.now(), 4.0, "test", "fed1", "complex", 3+4j),  # complex
        TSRecord(datetime.now(), 5.0, "test", "fed1", "vector", [1,2,3]), # list
    ]
    
    print(f"\nTested {len(records)} records with different data types:")
    for i, rec in enumerate(records):
        print(f"  {i+1}. {rec.data_name}: {rec.data_value} ({type(rec.data_value).__name__})")
    
    print("✓ TSRecord test complete")


if __name__ == "__main__":
    test_tsrecord()
    test_basic_functionality()
    test_with_federation_runner_data()
    print("\nAll tests completed!")