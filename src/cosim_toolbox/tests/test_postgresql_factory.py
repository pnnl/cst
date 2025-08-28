"""
Tests for updated timeseries factory with PostgreSQL support.
"""

import pytest
from pathlib import Path
from data_management.timeseries_factory import create_timeseries_manager
from data_management.csv_timeseries import CSVTimeSeriesManager
from data_management.postgresql_timeseries import PostgreSQLTimeSeriesManager


class TestTimeSeriesFactory:
    """Test time-series factory functions."""

    def test_create_csv_manager(self, temp_directory):
        """Test creating CSV manager via factory."""
        manager = create_timeseries_manager("csv", temp_directory, analysis_name="test")
        assert isinstance(manager, CSVTimeSeriesManager)
        assert manager.helper.location == Path(temp_directory)
        assert manager.analysis_name == "test"

    @pytest.mark.postgres
    def test_create_postgresql_manager_by_params(self):
        """Test creating PostgreSQL manager via individual parameters."""
        manager = create_timeseries_manager(
            "postgresql",
            "localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            schema_name="test_schema",
        )
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.helper.conn_params["host"] == "localhost"
        assert manager.helper.conn_params["port"] == 5432
        assert manager.helper.conn_params["database"] == "test_db"
        assert manager.helper.conn_params["user"] == "test_user"
        assert manager.helper.conn_params["password"] == "test_pass"
        assert manager.helper.analysis_name == "test_schema"

    @pytest.mark.postgres
    def test_create_postgresql_manager_by_url(self):
        """Test creating PostgreSQL manager via connection URL."""
        url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        manager = create_timeseries_manager(
            "postgresql", url, schema_name="test_schema"
        )
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.helper.conn_params["host"] == "localhost"
        assert manager.helper.conn_params["port"] == 5432
        assert manager.helper.conn_params["database"] == "test_db"
        assert manager.helper.conn_params["user"] == "test_user"
        assert manager.helper.conn_params["password"] == "test_pass"
        assert manager.helper.analysis_name == "test_schema"

    def test_invalid_backend(self):
        """Test error handling for invalid backend."""
        with pytest.raises(ValueError, match="Unknown backend"):
            create_timeseries_manager("invalid", "location")

    def test_case_insensitive_backend(self, temp_directory):
        """Test that backend names are case insensitive."""
        manager1 = create_timeseries_manager("CSV", temp_directory)
        manager2 = create_timeseries_manager("csv", temp_directory)

        assert all(isinstance(m, CSVTimeSeriesManager) for m in [manager1, manager2])

    @pytest.mark.postgres
    def test_postgresql_aliases(self):
        """Test that both 'postgresql' and 'postgres' work as backend names."""
        manager1 = create_timeseries_manager("postgresql", "localhost")
        manager2 = create_timeseries_manager("postgres", "localhost")

        assert all(
            isinstance(m, PostgreSQLTimeSeriesManager) for m in [manager1, manager2]
        )
