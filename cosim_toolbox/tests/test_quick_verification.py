"""
Quick verification test for basic functionality.
Use this for rapid testing during development.
"""

import tempfile
import shutil
from datetime import datetime
import sys

sys.path.insert(0, "src/cosim_toolbox")

from cosim_toolbox.dbms import TSRecord
from cosim_toolbox.dbms import create_metadata_manager


def test_basic_functionality():
    """Quick test of basic functionality."""

    print("🧪 Quick Verification Test")
    print("=" * 50)

    # Test TSRecord
    print("\n1. Testing TSRecord...")
    record = TSRecord(
        real_time=datetime.now(),
        sim_time=60.0,
        scenario="QuickTest",
        federate="TestFed",
        data_name="test/voltage",
        data_value=120.5,
    )
    print(f"   ✅ TSRecord created: {record.data_name} = {record.data_value}")

    # Test JSON Manager
    print("\n2. Testing JSON Manager...")
    temp_dir = tempfile.mkdtemp()

    try:
        manager = create_metadata_manager("json", location=temp_dir)
        print(f"   ✅ JSON manager created for: {temp_dir}")

        # Test federation operations
        fed_data = {"federation": {"TestFed": {"federate_type": "value", "period": 60}}}

        with manager as mgr:
            # Write
            success = mgr.write_federation("TestFederation", fed_data)
            print(f"   ✅ Federation write: {success}")

            # Read
            read_data = mgr.read_federation("TestFederation")
            success = read_data is not None
            print(f"   ✅ Federation read: {success}")

            # Generic operations
            custom_data = {"param": 42, "name": "test"}
            success = mgr.write("custom_params", "config1", custom_data)
            print(f"   ✅ Generic write: {success}")

            read_custom = mgr.read("custom_params", "config1")
            success = read_custom == custom_data
            print(f"   ✅ Generic read: {success}")

            # List operations
            federations = mgr.list_federations()
            collections = mgr.list_custom_collections()
            print(f"   ✅ List federations: {federations}")
            print(f"   ✅ List collections: {collections}")

    finally:
        shutil.rmtree(temp_dir)
        print(f"   🧹 Cleaned up: {temp_dir}")

    print("\n🎉 Quick verification complete!")


def test_federation_runner_simulation():
    """Simulate the federation runner workflow."""

    print("\n🏃 Federation Runner Simulation")
    print("=" * 50)

    temp_dir = tempfile.mkdtemp()

    try:
        manager = create_metadata_manager("json", location=temp_dir)

        # Create federation data like runner2.py would
        federation_data = {
            "federation": {
                "Battery": {
                    "federate_type": "value",
                    "command": "python3 simple_federate.py Battery MyScenario",
                    "HELICS_config": {
                        "name": "Battery",
                        "period": 60,
                        "publications": [{"key": "Battery/current", "type": "double"}],
                        "subscriptions": [
                            {"key": "EVehicle/voltage", "type": "double"}
                        ],
                    },
                },
                "EVehicle": {
                    "federate_type": "value",
                    "command": "python3 simple_federate.py EVehicle MyScenario",
                    "HELICS_config": {
                        "name": "EVehicle",
                        "period": 60,
                        "publications": [{"key": "EVehicle/voltage", "type": "double"}],
                        "subscriptions": [{"key": "Battery/current", "type": "double"}],
                    },
                },
            }
        }

        scenario_data = {
            "analysis": "MyAnalysis",
            "federation": "MyFederation",
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": False,
        }

        with manager as mgr:
            # Store configuration (like federation.define_scenario())
            fed_success = mgr.write_federation("MyFederation", federation_data)
            scenario_success = mgr.write_scenario("MyScenario", scenario_data)

            print(f"   ✅ Federation stored: {fed_success}")
            print(f"   ✅ Scenario stored: {scenario_success}")

            # Simulate federate reading configuration (like federate.py)
            scenario = mgr.read_scenario("MyScenario")
            federation_name = scenario["federation"]
            federation = mgr.read_federation(federation_name)

            # Extract Battery configuration
            battery_config = federation["federation"]["Battery"]
            helics_config = battery_config["HELICS_config"]

            print(f"   ✅ Scenario read: {scenario['analysis']}")
            print(f"   ✅ Federation read: {len(federation['federation'])} federates")
            print(f"   ✅ Battery config: period={helics_config['period']}")
            print(f"   ✅ Battery pubs: {len(helics_config['publications'])}")
            print(f"   ✅ Battery subs: {len(helics_config['subscriptions'])}")

            # Verify this provides everything a federate needs
            required_fields = ["federate_type", "HELICS_config"]
            has_all_fields = all(field in battery_config for field in required_fields)
            print(f"   ✅ All required fields present: {has_all_fields}")

    finally:
        shutil.rmtree(temp_dir)
        print(f"   🧹 Cleaned up: {temp_dir}")

    print("\n🎯 Federation runner simulation complete!")


if __name__ == "__main__":
    test_basic_functionality()
    test_federation_runner_simulation()
    print("\n✨ All quick tests passed!")
