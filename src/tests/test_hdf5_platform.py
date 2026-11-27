"""
Platform support of the HDF5 time-series backend. Runs on every platform.
"""

import pytest

import cosim_toolbox.dbms.hdf5_timeseries as M
from cosim_toolbox.dbms import HDF5TimeSeriesManager


@pytest.mark.parametrize("part", ["manager", "writer", "reader"])
def test_unsupported_platform_rejected_at_connect(tmp_path, monkeypatch, part):
    monkeypatch.setattr(M, "fcntl", None)  # what Windows looks like to the backend
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A")
    target = {"manager": m, "writer": m.writer, "reader": m.reader}[part]
    with pytest.raises(M.HDF5StoreError, match="requires POSIX file locking"):
        target.connect()
    assert not list(tmp_path.iterdir()), "nothing may be created on an unsupported platform"
