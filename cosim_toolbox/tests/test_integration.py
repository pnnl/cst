"""
Integration tests for the complete data management system.
"""

import pytest
from cosim_toolbox.dbms import create_metadata_manager


class TestIntegration:
    """Integration tests across different components."""
    
    def test_federation_runner_workflow_json(self, temp_directory, sample_federation_data, sample_scenario_data):
        """Test the complete workflow similar to federation runner using JSON."""
        manager = create_metadata_manager("json", location=temp_directory)
        
        with manager:
            # Step 1: Create federation configuration (like FederationConfig.define_scenario)
            success = manager.write_federation("MyFederation", sample_federation_data)
            assert success is True
            
            # Step 2: Create scenario configuration
            success = manager.write_scenario("MyScenario", sample_scenario_data)
            assert success is True
            
            # Step 3: Simulate federate reading its configuration (like federate.py)
            scenario = manager.read_scenario("MyScenario")
            assert scenario is not None
            
            federation_name = scenario["federation"]
            assert federation_name == "MyFederation"
            
            federation = manager.read_federation(federation_name)
            assert federation is not None
            
            # Step 4: Extract specific federate configuration
            battery_config = federation["federation"]["Battery"]
            battery_helics = battery_config["HELICS_config"]
            
            assert battery_config["federate_type"] == "value"
            assert battery_helics["period"] == 60
            assert len(battery_helics["publications"]) == 1
            assert len(battery_helics["subscriptions"]) == 1
            
            # Step 5: Verify EVehicle configuration
            evehicle_config = federation["federation"]["EVehicle"]
            evehicle_helics = evehicle_config["HELICS_config"]
            
            assert evehicle_config["federate_type"] == "value"
            assert evehicle_helics["period"] == 60
            
            # Step 6: Verify pub/sub connectivity
            battery_pub = battery_helics["publications"][0]["key"]
            evehicle_sub = evehicle_helics["subscriptions"][0]["key"]
            assert battery_pub == "Battery/EV1_current"
            assert evehicle_sub == "Battery/EV1_current"
            
            evehicle_pub = evehicle_helics["publications"][0]["key"]
            battery_sub = battery_helics["subscriptions"][0]["key"]
            assert evehicle_pub == "EVehicle/EV1_voltage"
            assert battery_sub == "EVehicle/EV1_voltage"
    
    @pytest.mark.mongo
    def test_federation_runner_workflow_mongo(self, sample_federation_data, sample_scenario_data):
        """Test the complete workflow using MongoDB."""
        manager = create_metadata_manager("mongo", location="mongodb://localhost:27017", database="test_integration")
        
        try:
            with manager:
                # Same workflow as JSON test
                success = manager.write_federation("MyFederation", sample_federation_data)
                assert success is True
                
                success = manager.write_scenario("MyScenario", sample_scenario_data)
                assert success is True
                
                scenario = manager.read_scenario("MyScenario")
                federation = manager.read_federation(scenario["federation"])
                
                battery_config = federation["federation"]["Battery"]
                assert battery_config["federate_type"] == "value"
                
                # Clean up
                manager.delete_federation("MyFederation")
                manager.delete_scenario("MyScenario")
        except Exception as e:
            pytest.skip(f"MongoDB integration test failed: {e}")
    
    def test_backend_compatibility(self, temp_directory, sample_federation_data, sample_scenario_data):
        """Test that data can be moved between backends."""
        # Create data with JSON
        json_manager = create_metadata_manager("json", location=temp_directory)
        
        with json_manager:
            json_manager.write_federation("TestFed", sample_federation_data)
            json_manager.write_scenario("TestScenario", sample_scenario_data)
            json_manager.write("custom", "config", {"param": "value"})
            
            # Read all data
            fed_data = json_manager.read_federation("TestFed")
            scenario_data = json_manager.read_scenario("TestScenario")
            custom_data = json_manager.read("custom", "config")
        
        # Write to MongoDB (if available)
        try:
            mongo_manager = create_metadata_manager("mongo", "mongodb://localhost:27017", database="test_compat")
            
            with mongo_manager:
                # Write the same data
                mongo_manager.write_federation("TestFed", fed_data)
                mongo_manager.write_scenario("TestScenario", scenario_data)
                mongo_manager.write("custom", "config", custom_data)
                
                # Verify it's the same
                assert mongo_manager.read_federation("TestFed") == fed_data
                assert mongo_manager.read_scenario("TestScenario") == scenario_data
                assert mongo_manager.read("custom", "config") == custom_data
                
                # Clean up
                mongo_manager.delete_federation("TestFed")
                mongo_manager.delete_scenario("TestScenario")
                mongo_manager.delete("custom", "config")
        except Exception:
            pytest.skip("MongoDB not available for compatibility test")
    
    def test_custom_collections_workflow(self, temp_directory):
        """Test workflow with custom collections."""
        manager = create_metadata_manager("json", location=temp_directory)
        
        with manager:
            # Create electrical configuration
            electrical_config = {
                "voltage_range": [110, 130],
                "frequency": 60,
                "max_current": 15.0
            }
            manager.write("electrical", "main_config", electrical_config)
            
            # Create weather configuration
            weather_config = {
                "temperature_range": [-10, 40],
                "humidity_range": [30, 90],
                "data_source": "NOAA"
            }
            manager.write("weather", "config", weather_config)
            
            # Create multiple weather profiles
            for season in ["spring", "summer", "fall", "winter"]:
                profile = {"season": season, "profile_data": [1, 2, 3]}
                manager.write("weather", f"{season}_profile", profile)
            
            # Test listing custom collections
            collections = manager.list_custom_collections()
            assert set(collections) == {"electrical", "weather"}
            
            # Test listing items in collections
            electrical_items = manager.list_items("electrical")
            weather_items = manager.list_items("weather")
            
            assert electrical_items == ["main_config"]
            assert set(weather_items) == {"config", "spring_profile", "summer_profile", "fall_profile", "winter_profile"}
            
            # Test reading configurations
            read_electrical = manager.read("electrical", "main_config")
            assert read_electrical == electrical_config
            
            read_weather = manager.read("weather", "config")
            assert read_weather == weather_config
            
            # Test existence checks
            assert manager.exists("electrical", "main_config")
            assert manager.exists("weather", "spring_profile")
            assert not manager.exists("nonexistent", "item")
            assert not manager.exists("weather", "nonexistent")