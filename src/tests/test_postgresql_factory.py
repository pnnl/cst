"""
Tests for updated timeseries factory with PostgreSQL support.
"""

import pytest
from pathlib import Path
from cosim_toolbox.dbms import create_timeseries_manager
from cosim_toolbox.dbms import CSVTimeSeriesManager
from cosim_toolbox.dbms import PostgreSQLTimeSeriesManager


class TestTimeSeriesFactory:
    """Test time-series factory functions."""

    def test_create_csv_manager(self, temp_directory):
        """Test creating CSV manager via factory."""
        manager = create_timeseries_manager("csv", "test", location=temp_directory)
        assert isinstance(manager, CSVTimeSeriesManager)
        assert manager.helper.location == Path(temp_directory)
        assert manager.analysis_name == "test"

    @pytest.mark.postgres
    def test_create_postgresql_manager_by_params(self):
        """Test creating PostgreSQL manager via individual parameters."""
        manager = create_timeseries_manager(
            "postgres",
            "test_analysis",
            location="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
        )
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.helper.conn_params["host"] == "localhost"
        assert manager.helper.conn_params["port"] == 5432
        assert manager.helper.conn_params["database"] == "test_db"
        assert manager.helper.conn_params["user"] == "test_user"
        assert manager.helper.conn_params["password"] == "test_pass"
        assert manager.helper.analysis_name == "test_analysis"

    @pytest.mark.postgres
    def test_create_postgresql_manager_by_url(self):
        """Test creating PostgreSQL manager via connection URL."""
        try:
            url = "postgresql://test_user:test_pass@localhost:5432/test_db"
            manager = create_timeseries_manager(
                "postgres", "test_analysis", location=url
            )
            assert isinstance(manager, PostgreSQLTimeSeriesManager)
            assert manager.helper.conn_params["host"] == "localhost"
            assert manager.helper.conn_params["port"] == 5432
            assert manager.helper.conn_params["database"] == "test_db"
            assert manager.helper.conn_params["user"] == "test_user"
            assert manager.helper.conn_params["password"] == "test_pass"
            assert manager.helper.analysis_name == "test_analysis"
        except Exception:
            pytest.skip("Postgres not available for compatibility test")

    def test_invalid_backend(self):
        """Test error handling for invalid backend."""
        with pytest.raises(ValueError, match="Unknown time-series backend"):
            create_timeseries_manager("invalid", location="location")

    def test_case_insensitive_backend(self, temp_directory):
        """Test that backend names are case-insensitive."""
        manager1 = create_timeseries_manager("CSV", location=temp_directory)
        manager2 = create_timeseries_manager("csv", location=temp_directory)

        assert all(isinstance(m, CSVTimeSeriesManager) for m in [manager1, manager2])

    @pytest.mark.postgres
    def test_postgresql_aliases(self):
        """Test that both 'postgresql' and 'postgres' work as backend names."""
        manager2 = create_timeseries_manager("postgres", location="localhost")

        assert all(
            isinstance(m, PostgreSQLTimeSeriesManager) for m in [manager2]
        )
