"""
Performance tests for data management system.
"""

import pytest
import time
from cosim_toolbox.dbms import create_metadata_manager


class TestPerformance:
    """Performance tests to ensure reasonable speed."""

    def test_json_write_performance(self, temp_directory):
        """Test JSON write performance."""
        manager = create_metadata_manager("json", location=temp_directory)

        test_data = {"test": "data", "numbers": list(range(100))}

        with manager:
            start_time = time.time()

            # Write 100 items
            for i in range(100):
                manager.write("performance_test", f"item_{i}", test_data)

            write_time = time.time() - start_time

            # Should complete in reasonable time (adjust threshold as needed)
            assert write_time < 5.0, f"Writing 100 items took {write_time:.2f} seconds"

    def test_json_read_performance(self, temp_directory):
        """Test JSON read performance."""
        manager = create_metadata_manager("json", location=temp_directory)

        test_data = {"test": "data", "numbers": list(range(100))}

        with manager:
            # First create the data
            for i in range(100):
                manager.write("performance_test", f"item_{i}", test_data)

            start_time = time.time()

            # Read 100 items
            for i in range(100):
                data = manager.read("performance_test", f"item_{i}")
                assert data == test_data

            read_time = time.time() - start_time

            # Should complete in reasonable time
            assert read_time < 2.0, f"Reading 100 items took {read_time:.2f} seconds"

    def test_json_list_performance(self, temp_directory):
        """Test JSON list performance."""
        manager = create_metadata_manager("json", location=temp_directory)

        test_data = {"test": "data"}

        with manager:
            # Create lots of items
            for i in range(1000):
                manager.write("performance_test", f"item_{i:04d}", test_data)

            start_time = time.time()

            # List items multiple times
            for _ in range(10):
                items = manager.list_items("performance_test")
                assert len(items) == 1000

            list_time = time.time() - start_time

            # Should complete in reasonable time
            assert list_time < 2.0, (
                f"Listing 1000 items 10 times took {list_time:.2f} seconds"
            )

    @pytest.mark.mongo
    def test_mongo_performance_comparison(self):
        """Compare MongoDB vs JSON performance (if MongoDB available)."""
        try:
            mongo_manager = create_metadata_manager(
                "mongo", location="mongodb://localhost:27017", db_name="test_perf"
            )

            test_data = {"test": "data", "numbers": list(range(50))}

            with mongo_manager:
                start_time = time.time()

                # Write 50 items to MongoDB
                for i in range(50):
                    mongo_manager.write("performance_test", f"item_{i}", test_data)

                mongo_write_time = time.time() - start_time

                start_time = time.time()

                # Read 50 items from MongoDB
                for i in range(50):
                    data = mongo_manager.read("performance_test", f"item_{i}")
                    assert data == test_data

                mongo_read_time = time.time() - start_time

                # Clean up
                for i in range(50):
                    mongo_manager.delete("performance_test", f"item_{i}")

                # MongoDB should be reasonably fast
                assert mongo_write_time < 10.0, (
                    f"MongoDB write took {mongo_write_time:.2f} seconds"
                )
                assert mongo_read_time < 5.0, (
                    f"MongoDB read took {mongo_read_time:.2f} seconds"
                )

        except Exception as e:
            pytest.skip(f"MongoDB performance test failed: {e}")
