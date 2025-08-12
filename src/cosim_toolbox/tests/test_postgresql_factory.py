"""
Tests for updated timeseries factory with PostgreSQL support.
"""

import pytest
from data_management.timeseries_factory import (
    create_timeseries_manager,
    create_csv_manager,
    create_postgresql_manager,
    create_postgresql_manager_from_url
)
from cosim_toolbox.csv_timeseries import CSVTimeSeriesManager
from cosim_toolbox.postgresql_timeseries import PostgreSQLTimeSeriesManager


class TestTimeSeriesFactory:
    """Test time-series factory functions."""
    
    def test_create_csv_manager(self, temp_directory):
        """Test creating CSV manager via factory."""
        manager = create_timeseries_manager("csv", temp_directory, analysis_name="test")
        assert isinstance(manager, CSVTimeSeriesManager)
        assert manager.location == temp_directory
        assert manager.analysis_name == "test"
    
    def test_create_csv_manager_convenience(self, temp_directory):
        """Test convenience function for CSV manager."""
        manager = create_csv_manager(temp_directory, "test_analysis")
        assert isinstance(manager, CSVTimeSeriesManager)
        assert manager.analysis_name == "test_analysis"
    
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
            schema_name="test_schema"
        )
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.host == "localhost"
        assert manager.port == 5432
        assert manager.database == "test_db"
        assert manager.user == "test_user"
        assert manager.password == "test_pass"
        assert manager.schema_name == "test_schema"
    
    @pytest.mark.postgres
    def test_create_postgresql_manager_by_url(self):
        """Test creating PostgreSQL manager via connection URL."""
        url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        manager = create_timeseries_manager("postgresql", url, schema_name="test_schema")
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.host == "localhost"
        assert manager.port == 5432
        assert manager.database == "test_db"
        assert manager.user == "test_user"
        assert manager.password == "test_pass"
        assert manager.schema_name == "test_schema"
    
    @pytest.mark.postgres
    def test_create_postgresql_manager_convenience(self):
        """Test convenience function for PostgreSQL manager."""
        manager = create_postgresql_manager(
            host="test_host",
            database="test_db",
            schema_name="test_schema"
        )
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.host == "test_host"
        assert manager.database == "test_db"
        assert manager.schema_name == "test_schema"
    
    @pytest.mark.postgres
    def test_create_postgresql_manager_from_url_convenience(self):
        """Test convenience function for PostgreSQL manager from URL."""
        url = "postgresql://user:pass@host:5432/db"
        manager = create_postgresql_manager_from_url(url, schema_name="test")
        assert isinstance(manager, PostgreSQLTimeSeriesManager)
        assert manager.host == "host"
        assert manager.user == "user"
        assert manager.password == "pass"
        assert manager.database == "db"
        assert manager.schema_name == "test"
    
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
        
        assert all(isinstance(m, PostgreSQLTimeSeriesManager) for m in [manager1, manager2])
    
    @pytest.mark.postgres
    def test_invalid_postgresql_url(self):
        """Test error handling for invalid PostgreSQL URLs."""
        with pytest.raises(ValueError, match="Invalid PostgreSQL connection string"):
            create_timeseries_manager("postgresql", "invalid://url")