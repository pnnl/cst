"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Test data fixtures
@pytest.fixture
def sample_federation_data() -> Dict[str, Any]:
    """Sample federation configuration data."""
    return {
        "federation": {
            "Battery": {
                "logger": False,
                "image": "cosim-cst:latest",
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
                            "key": "EVehicle/EV1_voltage",
                            "type": "double",
                            "unit": "V"
                        }
                    ]
                }
            },
            "EVehicle": {
                "logger": False,
                "image": "cosim-cst:latest",
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
                            "key": "Battery/EV1_current",
                            "type": "double",
                            "unit": "A"
                        }
                    ]
                }
            }
        }
    }

@pytest.fixture
def sample_scenario_data() -> Dict[str, Any]:
    """Sample scenario configuration data."""
    return {
        "analysis": "MyAnalysis",
        "federation": "MyFederation",
        "start_time": "2023-12-07T15:31:27",
        "stop_time": "2023-12-08T15:31:27",
        "docker": False
    }

@pytest.fixture
def sample_custom_data() -> Dict[str, Any]:
    """Sample custom configuration data."""
    return {
        "voltage_range": [110, 130],
        "frequency": 60,
        "parameters": {
            "max_current": 15.0,
            "efficiency": 0.95
        },
        "active": True
    }

@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_ts_records():
    """Sample time-series records for testing."""
    from cosim_toolbox.dbms import TSRecord
    
    base_time = datetime(2023, 12, 7, 15, 31, 27)
    
    return [
        TSRecord(
            real_time=base_time,
            sim_time=0.0,
            scenario="TestScenario",
            federate="Battery",
            data_name="Battery/current",
            data_value=10.5
        ),
        TSRecord(
            real_time=base_time,
            sim_time=60.0,
            scenario="TestScenario", 
            federate="Battery",
            data_name="Battery/current",
            data_value=12.3
        ),
        TSRecord(
            real_time=base_time,
            sim_time=0.0,
            scenario="TestScenario",
            federate="EVehicle",
            data_name="EVehicle/voltage", 
            data_value=120.0
        )
    ]

# Skip MongoDB tests if pymongo is not available
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "mongo: mark test as requiring MongoDB (pymongo)"
    )

def pytest_collection_modifyitems(config, items):
    """Skip MongoDB tests if pymongo is not available."""
    try:
        import pymongo
        mongo_available = True
    except ImportError:
        mongo_available = False
    
    if not mongo_available:
        skip_mongo = pytest.mark.skip(reason="pymongo not available")
        for item in items:
            if "mongo" in item.keywords:
                item.add_marker(skip_mongo)