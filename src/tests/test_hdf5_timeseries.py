"""
Tests for the HDF5 time-series backend.
"""

import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

import cosim_toolbox
import cosim_toolbox.dbms.hdf5_timeseries as M
from cosim_toolbox.dbms import HDF5TimeSeriesManager, create_timeseries_manager
from cosim_toolbox.dbms.hdf5_timeseries import (
    DATA_TYPES,
    HDF5Helper,
    HDF5StoreError,
    HDF5TimeSeriesReader,
    HDF5TimeSeriesWriter,
    UnsupportedDataTypeError,
    canonical_data_type,
    decode_name,
    encode_name,
)
from cosim_toolbox.dbms.time_series_record import TSRecord
from cosim_toolbox.dbms.validation import ValidationError

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
import hdf5_workload as W

T0 = datetime(2026, 1, 1, 12, 0, 0, 123456, tzinfo=UTC)
POSIX = sys.platform != "win32"
# The backend needs POSIX file locking; elsewhere connect() refuses (see test_hdf5_platform.py).
pytestmark = pytest.mark.skipif(M.fcntl is None, reason="HDF5 backend requires POSIX file locking")


def rec(t=0.0, v=1.0, fed="Battery", name="Battery/current", dt=None, scen="s1", rt=T0, **kw):
    return TSRecord(real_time=rt, sim_time=t, scenario=scen, federate=fed, data_name=name,
                    data_value=v, data_type=dt, **kw)


@pytest.fixture
def mgr(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=4)
    m.connect()
    yield m
    m.disconnect()


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return (math.isnan(a) and math.isnan(b)) or (a == b and math.copysign(1, a) == math.copysign(1, b))
    if isinstance(a, complex) and isinstance(b, complex):
        return same(a.real, b.real) and same(a.imag, b.imag)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


# ------------------------------------------------------------------ data types
ROUND_TRIPS = [
    ("hdt_boolean", True), ("hdt_boolean", False), ("hdt_boolean", np.bool_(True)),
    ("hdt_integer", 0), ("hdt_integer", 2**63 - 1), ("hdt_integer", -(2**63)), ("hdt_integer", np.int32(-5)),
    ("hdt_double", 0.0), ("hdt_double", -0.0), ("hdt_double", math.inf), ("hdt_double", -math.inf),
    ("hdt_double", 5e-324), ("hdt_double", 1.7976931348623157e308), ("hdt_double", 2**53),
    ("hdt_double", np.float32(0.1)),
    ("hdt_complex", 1.5 - 2j), ("hdt_complex", complex(math.inf, -math.inf)), ("hdt_complex", 0j),
    ("hdt_complex", np.complex64(1 + 2j)), ("hdt_complex", 3.0),
    ("hdt_string", ""), ("hdt_string", "Δ€😀 नमस्ते"), ("hdt_string", "a\nb\t'\"c"),
    ("hdt_vector", []), ("hdt_vector", [1.0, -0.0, math.inf, 1e-300]), ("hdt_vector", [1, 2, 3]),
    ("hdt_vector", list(np.linspace(0, 1, 5000))), ("hdt_vector", np.array([1.5, 2.5], dtype=np.float32)),
    ("hdt_complex_vector", []), ("hdt_complex_vector", [1 + 2j, -3.5 - 4j, complex(math.inf, 0)]),
    ("hdt_complex_vector", [1.0, 2]),
]


def expected_value(dt, v):
    if dt == "hdt_boolean":
        return bool(v)
    if dt == "hdt_integer":
        return int(v)
    if dt == "hdt_double":
        return float(v)
    if dt == "hdt_complex":
        return complex(v)
    if dt == "hdt_vector":
        return [float(x) for x in v]
    if dt == "hdt_complex_vector":
        return [complex(x) for x in v]
    return v


@pytest.mark.parametrize("dt,v", ROUND_TRIPS, ids=[f"{d}-{i}" for i, (d, _) in enumerate(ROUND_TRIPS)])
def test_round_trip(mgr, dt, v):
    assert mgr.write_records([rec(v=v, dt=dt)])
    df = mgr.read_data()
    assert len(df) == 1
    assert same(expected_value(dt, v), df["data_value"].iloc[0])
    assert df["real_time"].iloc[0] == T0 and str(df["real_time"].dt.tz) == "UTC"


@pytest.mark.parametrize("dt,text,value", [("hdt_complex", "(-1e+49+1j)", complex(-1e49, 1)),
                                           ("hdt_complex", " 2-3j ", 2 - 3j), ("hdt_double", "0.1", 0.1),
                                           ("hdt_double", "-inf", -math.inf), ("hdt_integer", "-42", -42)])
def test_numeric_strings_parsed_like_helics(mgr, dt, text, value):
    """CST federates log the raw published value; the test federation publishes complex values as strings."""
    assert mgr.write_records([rec(v=text, dt=dt)])
    assert same(value, mgr.read_data()["data_value"].iloc[0])


def test_nan_values(mgr):
    assert mgr.write_records([rec(0, math.nan, dt="hdt_double"), rec(1, [math.nan], dt="hdt_vector"),
                              rec(2, complex(math.nan, 1), dt="hdt_complex")])
    v = mgr.read_data()["data_value"]
    assert math.isnan(v[0]) and math.isnan(v[1][0]) and math.isnan(v[2].real) and v[2].imag == 1


def test_auto_detected_types(mgr):
    assert mgr.write_records([rec(0, True), rec(1, 7), rec(2, 1.25), rec(3, 2j), rec(4, "x"), rec(5, [1.0])])
    assert [type(x) for x in mgr.read_data()["data_value"]] == [bool, int, float, complex, str, list]


@pytest.mark.parametrize("payload", ["", "ascii", "Δ€😀", b"", b"\xff\x00\xfe\x80", b"a\x00b",
                                     bytes(range(256)) * 40])
def test_endpoint_payload_preserved(mgr, payload):
    r = rec(v=payload, name="Battery/ep", receiving_federate="EV", receiving_endpoint="EV/ep")
    assert r.data_type == "hdt_endpoint" and mgr.write_records([r])
    df = mgr.read_data(data_type="hdt_endpoint")
    out = df["data_value"].iloc[0]
    assert type(out) is type(payload) and out == payload
    assert (df["receiving_federate"].iloc[0], df["receiving_endpoint"].iloc[0]) == ("EV", "EV/ep")


def test_endpoint_none_and_empty_metadata_distinct(mgr):
    assert mgr.write_records([rec(0, "m", dt="hdt_endpoint", receiving_federate=None, receiving_endpoint="X/ep"),
                              rec(1, "m", dt="hdt_endpoint", receiving_federate="", receiving_endpoint="")])
    df = mgr.read_data()
    assert df["receiving_federate"][0] is None and df["receiving_endpoint"][0] == "X/ep"
    assert df["receiving_federate"][1] == "" and df["receiving_endpoint"][1] == ""


@pytest.mark.parametrize("alias,canon", [("hdt_float", "hdt_double"), ("hdt_int", "hdt_integer"),
                                         ("hdt_int64", "hdt_integer"), ("hdt_bool", "hdt_boolean"),
                                         ("hdt_double_vector", "hdt_vector"),
                                         ("hdt_complex vector", "hdt_complex_vector"), ("HDT_DOUBLE", "hdt_double")])
def test_aliases(alias, canon):
    assert canonical_data_type(alias) == canon


@pytest.mark.parametrize("bad", ["hdt_named_point", "hdt_time", "hdt_json", "hdt_raw", "hdt_any", "hdt_bogus", "hdt_"])
def test_unsupported_types(mgr, bad):
    with pytest.raises(UnsupportedDataTypeError):
        canonical_data_type(bad)
    assert not mgr.write_records([rec(v="x", dt=bad)])
    assert mgr.read_data().empty


LOSSY = [
    ("hdt_integer", 2**63), ("hdt_integer", True), ("hdt_integer", 1.0), ("hdt_boolean", 1),
    ("hdt_double", "abc"), ("hdt_double", 2**53 + 1), ("hdt_double", True), ("hdt_integer", "1.5"),
    ("hdt_complex", "1+2i"), ("hdt_integer", str(2**63)),
    ("hdt_string", "a\x00b"), ("hdt_string", "\ud800"), ("hdt_string", b"x"),
    ("hdt_vector", [1j]), ("hdt_vector", "abc"), ("hdt_vector", [2**53 + 1]), ("hdt_vector", [True]),
    ("hdt_vector", np.zeros((2, 2))), ("hdt_complex_vector", ["a"]), ("hdt_complex_vector", [2**60 + 1]),
    ("hdt_complex", 2**53 + 1), ("hdt_endpoint", 5), ("hdt_endpoint", "\udc80"),
]
if np.finfo(np.longdouble).bits > 64:  # extended precision available on this platform
    LOSSY += [("hdt_double", np.longdouble(1) + np.finfo(np.longdouble).eps),
              ("hdt_vector", np.array([np.longdouble(1) + np.finfo(np.longdouble).eps])),
              ("hdt_complex", np.clongdouble(1 + np.finfo(np.longdouble).eps))]


@pytest.mark.parametrize("dt,v", LOSSY, ids=[f"{d}-{i}" for i, (d, _) in enumerate(LOSSY)])
def test_lossy_values_rejected_atomically(mgr, dt, v):
    assert not mgr.write_records([rec(0, 1.0, dt="hdt_double"), rec(1, v, dt=dt)])
    assert mgr.read_data().empty, "a rejected batch must write nothing"


@pytest.mark.parametrize("rt", [datetime(2263, 1, 1, tzinfo=UTC), datetime(1600, 1, 1, tzinfo=UTC),
                                datetime(1677, 9, 21, tzinfo=UTC), "2026-01-01"])
def test_unrepresentable_timestamps_rejected_before_io(mgr, tmp_path, rt):
    assert not mgr.write_records([rec(rt=rt)])
    assert not list((tmp_path / "A").glob("*.h5*"))


def test_timestamp_precision_and_timezones(mgr):
    tz = timezone(timedelta(hours=-6))
    naive = datetime(2026, 1, 1, 12, 0, 0, 1)
    assert mgr.write_records([rec(0, rt=datetime(2026, 1, 1, 6, 0, 0, 999999, tzinfo=tz)),
                              rec(1, rt=naive), rec(2, rt=datetime(2262, 4, 11, tzinfo=UTC))])
    rt = mgr.read_data()["real_time"]
    assert rt[0] == datetime(2026, 1, 1, 12, 0, 0, 999999, tzinfo=UTC)
    assert rt[1] == naive.replace(tzinfo=UTC)  # naive values are taken as UTC, as in the Parquet backend
    assert rt[2] == datetime(2262, 4, 11, tzinfo=UTC)


def test_invalid_names_and_text_rejected(mgr):
    assert not mgr.write_records([rec(fed="")])
    assert not mgr.write_records([rec(fed="bad|name")])
    assert not mgr.write_records([rec(scen="x\x00")])
    assert not mgr.write_records([rec(name=5)])
    assert not mgr.write_records([rec(t=math.nan)])


# ------------------------------------------------------------------ append / buffering / retry
def test_append_many_flush_cycles_and_consolidation(mgr, tmp_path):
    for cycle in range(25):
        for j in range(40):
            mgr.add_record(rec(cycle * 40 + j, float(cycle * 40 + j)))
        assert mgr.flush() and mgr.buffer_size == 0
    assert mgr.read_data()["sim_time"].tolist() == [float(i) for i in range(1000)]
    assert len(list((tmp_path / "A" / "Battery.h5.segments").glob("*.h5"))) < 4
    mgr.disconnect()
    assert not (tmp_path / "A" / "Battery.h5.segments").exists()
    mgr.connect()
    assert len(mgr.read_data()) == 1000


def test_persistence_across_reconnect(tmp_path):
    for i in range(3):
        with HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A") as m:
            assert m.write_records([rec(i, float(i))])
    with HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A") as m:
        assert m.read_data()["sim_time"].tolist() == [0.0, 1.0, 2.0]


@pytest.mark.parametrize("max_segments", [1, 3, 32])
def test_all_types_many_batches_exact(tmp_path, max_segments):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=max_segments)
    m.connect()
    expected = []
    for k in range(7):
        batch = W.make_batch("F", k, 5)
        expected += [W.key_of_record(r) for r in batch]
        for r in batch:
            m.add_record(r)
        assert m.flush()
    assert sorted(W.keys_of_frame(m.read_data())) == sorted(expected)
    m.disconnect(); m.connect()
    assert sorted(W.keys_of_frame(m.read_data())) == sorted(expected)


def _fail_once(monkeypatch, attr, obj=M, when="before", predicate=lambda *a, **k: True):
    orig = getattr(obj, attr)
    state = {"done": False}

    def wrapper(*a, **k):
        if not state["done"] and predicate(*a, **k):
            state["done"] = True
            if when == "before":
                raise OSError("injected failure")
            orig(*a, **k)
            raise OSError("injected failure after success")
        return orig(*a, **k)

    monkeypatch.setattr(obj, attr, wrapper)


def test_retry_after_partial_multi_file_failure_no_duplicates(tmp_path, monkeypatch):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    for f in ("F1", "F2", "F3"):
        m.add_record(rec(0, 1.0, fed=f))
    _fail_once(monkeypatch, "_commit_segment", predicate=lambda helper, fed, *a: fed == "F2")
    assert not m.flush() and m.buffer_size == 3
    m.add_record(rec(1, 2.0, fed="F1"))
    assert m.flush()
    df = m.read_data()
    assert sorted(zip(df["federate"], df["sim_time"])) == [("F1", 0.0), ("F1", 1.0), ("F2", 0.0), ("F3", 0.0)]


@pytest.mark.parametrize("attr,obj", [("_fsync_dir", M), ("replace", os)])
def test_retry_after_lost_acknowledgement_no_duplicates(tmp_path, monkeypatch, attr, obj):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    m.add_record(rec(0, 1.0, fed="F1")); m.add_record(rec(0, 1.0, fed="F2"))
    _fail_once(monkeypatch, attr, obj, when="after")  # batch published, then an error is reported
    assert not m.flush()
    assert m.flush()
    assert len(m.read_data()) == 2


def test_retry_dedup_has_no_expiry(tmp_path, monkeypatch):
    """Earlier prototype kept 32 tokens; now dedup holds after any number of intervening commits."""
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=2); m.connect()
    other = HDF5TimeSeriesWriter(helper=HDF5Helper(str(tmp_path), "A", max_segments=2)); other.connect()
    m.add_record(rec(0, 1.0, fed="F", scen="mine"))
    _fail_once(monkeypatch, "replace", os, when="after")
    assert not m.flush()  # committed, acknowledgement lost
    for i in range(100):  # other writer commits 100 batches (and consolidations) in between
        other.add_record(rec(1 + i, 1.0, fed="F", scen="other")); assert other.flush()
    assert m.flush()
    df = m.read_data()
    assert (df["scenario"] == "mine").sum() == 1 and (df["scenario"] == "other").sum() == 100


def test_direct_write_records_calls_are_independent(mgr):
    r = [rec(0, 1.0)]
    assert mgr.write_records(r) and mgr.write_records(r)
    assert len(mgr.read_data()) == 2


def test_invalid_record_in_buffer_is_reported_not_silent(mgr):
    mgr.add_record(rec(0, 1.0)); mgr.add_record(rec(1, "x", dt="hdt_named_point")); mgr.add_record(rec(2, 2.0))
    assert not mgr.flush(), "flush must not report success when a record was not stored"
    assert len(mgr.writer.rejected) == 1 and mgr.buffer_size == 0
    assert mgr.read_data()["sim_time"].tolist() == [0.0, 2.0]
    mgr.add_record(rec(3, 3.0))
    assert mgr.flush(), "an invalid record must not block later flushes"


def test_failed_io_keeps_records_pending(mgr, monkeypatch):
    mgr.add_record(rec(0, 1.0))
    _fail_once(monkeypatch, "_commit_segment")
    assert not mgr.flush() and mgr.buffer_size == 1
    assert mgr.flush() and mgr.buffer_size == 0 and len(mgr.read_data()) == 1


def test_consolidation_failure_keeps_data_committed(tmp_path, monkeypatch):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=1); m.connect()
    _fail_once(monkeypatch, "_append_columns")
    assert m.write_records([rec(0, 1.0)])  # segment committed; consolidation failed and is logged
    assert len(m.read_data()) == 1
    assert m.consolidate() and len(m.read_data()) == 1
    assert not list((tmp_path / "A").glob("*.tmp-*"))


# ------------------------------------------------------------------ analysis name contract
def test_analysis_name_setter(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    assert m.write_records([rec(0, 1.0)])
    m.analysis_name = "B"
    assert m.analysis_name == "B" and m.helper.analysis_path == tmp_path / "B"
    assert m.read_data().empty and m.write_records([rec(1, 2.0)])
    assert len(m.read_data()) == 1
    m.analysis_name = "A"
    assert m.read_data()["sim_time"].tolist() == [0.0]
    with pytest.raises(ValidationError):
        m.analysis_name = "x/../../y"


def test_analysis_change_refused_while_records_pending(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    m.add_record(rec(0, 1.0))
    with pytest.raises(ValueError):
        m.analysis_name = "B"
    assert m.analysis_name == "A" and m.flush()
    m.analysis_name = "B"
    assert m.read_data().empty


@pytest.mark.parametrize("name", ["a/b", "x/../../escape", "..", ".", "a\\b", ""])
def test_analysis_name_containment(tmp_path, name):
    with pytest.raises(ValidationError):
        HDF5TimeSeriesManager(location=str(tmp_path), analysis_name=name)


# ------------------------------------------------------------------ path safety
@pytest.mark.parametrize("fed", ["Battery/ep1", "a/../../escape", "Δ federate", "con.txt", "COM1.log", "100%",
                                 "a%2Fb", "a.b.c"])
def test_federate_names_contained_and_reversible(tmp_path, fed):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    assert m.write_records([rec(fed=fed)])
    m.disconnect(); m.connect()
    assert all(p.resolve().parent == (tmp_path / "A").resolve() for p in (tmp_path / "A").iterdir())
    assert [p for p in tmp_path.iterdir()] == [tmp_path / "A"]
    assert m.list_federates() == [fed] and len(m.read_data(federate_name=fed)) == 1


@pytest.mark.parametrize("fed", ["CON", "x.", ".hidden", " lead"])
def test_names_rejected_by_cst_validation(mgr, fed):
    assert not mgr.write_records([rec(fed=fed)])


def test_encoding_round_trip_examples():
    for name in ["Battery", "Battery/EV1", "μGrid", "東京", "a%b", ".x", "x.", "CON", "nul.txt"]:
        enc = encode_name(name)
        assert decode_name(enc) == name and "/" not in enc and not enc.startswith(".")
    with pytest.raises(ValueError):
        decode_name("bad/name")


def test_case_variant_federate_refused(mgr, tmp_path):
    assert mgr.write_records([rec(fed="Fed")])
    assert not mgr.write_records([rec(fed="fed")])
    assert mgr.list_federates() == ["Fed"]


def test_case_insensitive_alias_detected_by_attribute(mgr, tmp_path):
    """On a case-insensitive filesystem 'fed' opens 'Fed.h5'; the stored federate attribute catches it."""
    assert mgr.write_records([rec(fed="Fed")]); mgr.consolidate()
    os.link(tmp_path / "A" / "Fed.h5", tmp_path / "A" / "fed2.h5")
    with pytest.raises(HDF5StoreError, match="belongs to federate"):
        mgr.read_data(federate_name="fed2")


@pytest.mark.skipif(not POSIX, reason="symlink creation")
def test_symlinked_analysis_directory_refused(tmp_path):
    outside = tmp_path / "outside"; outside.mkdir()
    (tmp_path / "store").mkdir(); (tmp_path / "store" / "A").symlink_to(outside)
    m = HDF5TimeSeriesManager(location=str(tmp_path / "store"), analysis_name="A")
    assert not m.connect()
    assert not list(outside.iterdir())


@pytest.mark.skipif(not POSIX, reason="symlink creation")
@pytest.mark.parametrize("target", ["Fed.h5", "Fed.h5.lock", "Fed.h5.segments"])
def test_symlinked_federate_paths_refused(mgr, tmp_path, target):
    victim = tmp_path / "victim"; victim.mkdir() if target.endswith("segments") else victim.write_bytes(b"keep")
    (tmp_path / "A" / target).symlink_to(victim)
    assert not mgr.write_records([rec(fed="Fed")])
    if victim.is_file():
        assert victim.read_bytes() == b"keep"
    else:
        assert not list(victim.iterdir())


# ------------------------------------------------------------------ schema validation / no silent loss
def _committed_file(mgr, tmp_path):
    assert mgr.write_records([rec(0, 1.0), rec(1, "s")]) and mgr.consolidate()
    return tmp_path / "A" / "Battery.h5"


@pytest.mark.parametrize("damage", ["drop_attr", "wrong_version", "drop_dataset", "short_dataset", "wrong_dtype",
                                    "extra_object", "nrows_mismatch", "garbage"])
def test_damaged_file_is_reported_not_silently_skipped(mgr, tmp_path, damage):
    path = _committed_file(mgr, tmp_path)
    if damage == "garbage":
        path.write_bytes(b"not an hdf5 file")
    else:
        with h5py.File(path, "a") as f:
            g = f["hdt_double"]
            if damage == "drop_attr":
                del f.attrs["federate"]
            elif damage == "wrong_version":
                f.attrs["schema_version"] = "99"
            elif damage == "drop_dataset":
                del g["scenario"]
            elif damage == "short_dataset":
                g["sim_time"].resize((0,))
            elif damage == "wrong_dtype":
                del g["sim_time"]; g.create_dataset("sim_time", data=np.array(["x"], dtype=object),
                                                    dtype=h5py.string_dtype(), maxshape=(None,))
            elif damage == "extra_object":
                f.create_group("surprise")
            elif damage == "nrows_mismatch":
                g.attrs["nrows"] = 5
    with pytest.raises(HDF5StoreError):
        mgr.read_data()
    assert not mgr.write_records([rec(5, 1.0)]), "writer must refuse to build on a damaged file"


def test_damaged_segment_is_reported(mgr, tmp_path):
    assert mgr.write_records([rec(0, 1.0)])
    seg = next((tmp_path / "A" / "Battery.h5.segments").glob("*.h5"))
    seg.write_bytes(b"\x89HDF\r\n\x1a\n broken")
    with pytest.raises(HDF5StoreError):
        mgr.read_data()


# ------------------------------------------------------------------ filters, listing, empty
def test_filters_and_listing(mgr):
    recs = [rec(t, float(t), fed=f, scen=s, name=n) for t in range(10) for f in ("F1", "F2")
            for s in ("s1", "s2") for n in ("a", "b's")]
    recs.append(rec(3, "txt", fed="F1"))
    assert mgr.write_records(recs)
    assert len(mgr.read_data()) == 81
    assert len(mgr.read_data(federate_name="F1", scenario_name="s2", data_name="b's")) == 10
    assert set(mgr.read_data(start_time=2, duration=3)["sim_time"]) == {2.0, 3.0, 4.0}
    assert len(mgr.read_data(data_type="hdt_string")) == 1
    assert len(mgr.read_data(data_type=["hdt_float"])) == 80
    assert len(mgr.read_data(federate_name=["F2", "nobody"])) == 40
    assert mgr.list_federates() == ["F1", "F2"] and mgr.list_scenarios() == ["s1", "s2"]
    assert mgr.list_data_types(["F1"]) == ["hdt_double", "hdt_string"]
    assert mgr.list_data_types() == ["hdt_double", "hdt_double", "hdt_string"]
    assert mgr.get_time_range() == {"min_time": 0.0, "max_time": 9.0}


def test_empty_and_missing(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "nothing"), analysis_name="A")
    m.reader.connect()
    assert m.read_data().empty and m.list_federates() == [] and m.list_scenarios() == []
    assert m.get_time_range() == {"min_time": 0.0, "max_time": 0.0}
    m.connect()
    assert m.write_records([]) and m.read_data(federate_name="nobody").empty


def test_not_connected(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A")
    assert not m.write_records([rec()]) and m.read_data().empty and m.list_federates() == []


def test_standalone_reader_and_writer(tmp_path):
    with HDF5TimeSeriesWriter(location=str(tmp_path), analysis_name="A") as w:
        assert w.write_records([rec()])
    with HDF5TimeSeriesReader(location=str(tmp_path), analysis_name="A") as r:
        assert len(r.read_data()) == 1
    with pytest.raises(ValueError):
        HDF5TimeSeriesWriter()
    with pytest.raises(ValueError):
        HDF5Helper(str(tmp_path), "A", compression="zstd")


# ------------------------------------------------------------------ delete / backup
def test_delete_federate(mgr, tmp_path):
    assert mgr.write_records([rec(fed="F1"), rec(fed="F2")])
    assert mgr.delete_federate_data("F1") and mgr.list_federates() == ["F2"]
    assert not mgr.delete_federate_data("F1") and not mgr.delete_federate_data("bad|name")
    with pytest.raises(NotImplementedError):
        mgr.delete_scenario_data("s1")


def test_backup_round_trip(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "src"), analysis_name="A"); m.connect()
    assert m.write_records([rec(t, float(t), fed=f) for t in range(50) for f in ("F1", "F2/x")])
    assert m.backup_analysis(str(tmp_path / "bak" / "A"))
    b = HDF5TimeSeriesManager(location=str(tmp_path / "bak"), analysis_name="A"); b.connect()
    assert b.read_data().equals(m.read_data())
    assert sorted(p.name for p in (tmp_path / "bak" / "A").iterdir()) == ["F1.h5", "F2%2Fx.h5"]
    empty = HDF5TimeSeriesManager(location=str(tmp_path / "none"), analysis_name="A")
    assert empty.backup_analysis(str(tmp_path / "bak2"))


@pytest.mark.skipif(not POSIX, reason="multiprocessing lock test uses fork-free subprocess + flock")
def test_delete_and_backup_wait_for_writer_lock(mgr, tmp_path):
    assert mgr.write_records([rec(fed="F1")])
    holder = subprocess.Popen([sys.executable, "-c", (
        "import fcntl, os, sys, time; fd = os.open(sys.argv[1], os.O_RDWR); fcntl.flock(fd, fcntl.LOCK_EX); "
        "print('locked', flush=True); time.sleep(2)"), str(tmp_path / "A" / "F1.h5.lock")],
        stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "locked"
    mgr.helper.lock_timeout = 0.3
    assert not mgr.delete_federate_data("F1") and not mgr.backup_analysis(str(tmp_path / "bak"))
    assert not mgr.write_records([rec(1, fed="F1")])
    holder.wait()
    mgr.helper.lock_timeout = 10
    assert mgr.backup_analysis(str(tmp_path / "bak")) and mgr.delete_federate_data("F1")


# ------------------------------------------------------------------ factory integration
def test_factory_creates_hdf5_manager(tmp_path):
    with create_timeseries_manager("HDF5", "factory_test", location=str(tmp_path), max_segments=2,
                                   unknown_option=1) as m:
        assert isinstance(m, HDF5TimeSeriesManager) and m.helper.max_segments == 2
        assert m.write_records([rec()]) and len(m.read_data()) == 1
    assert (tmp_path / "factory_test" / "Battery.h5").is_file()
    with pytest.raises(ValueError, match="hdf5"):
        create_timeseries_manager("nosuch", "x")


def test_data_types_constant():
    assert len(DATA_TYPES) == 8 and set(W.TYPES) == set(DATA_TYPES)


# ------------------------------------------------------------------ multi-process
def _child(tmp_path, *args, timeout=60):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(TESTS_DIR.parent), str(TESTS_DIR)]))
    return subprocess.run([sys.executable, str(TESTS_DIR / "hdf5_workload.py"), str(tmp_path), "A", *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=timeout, check=False)


def _acked(stdout):
    return [int(line.split()[1]) for line in stdout.splitlines() if line.startswith("ACK")]


@pytest.mark.skipif(not POSIX, reason="concurrent writers rely on POSIX flock and rename semantics")
def test_concurrent_writer_processes_same_and_different_federates(tmp_path):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(TESTS_DIR.parent), str(TESTS_DIR)]))
    cmd = lambda fed, first: [sys.executable, str(TESTS_DIR / "hdf5_workload.py"), str(tmp_path), "A",
                              fed, str(first), "12", "3", "4", "none", "-1"]
    procs = [subprocess.Popen(cmd(f, first), stdout=subprocess.PIPE, text=True, env=env)
             for f, first in (("Shared", 0), ("Shared", 100), ("Own", 0))]
    outs = [p.communicate(timeout=120)[0] for p in procs]
    assert all("DONE" in o for o in outs)
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.reader.connect()
    expected = [W.key_of_record(r) for f, first in (("Shared", 0), ("Shared", 100), ("Own", 0))
                for k in range(first, first + 12) for r in W.make_batch(f, k, 3)]
    assert sorted(W.keys_of_frame(m.read_data())) == sorted(expected)


@pytest.mark.skipif(not POSIX, reason="SIGKILL")
@pytest.mark.parametrize("point", W.SEGMENT_POINTS + W.CONSOLIDATION_POINTS)
def test_kill_at_every_commit_stage_loses_no_acknowledged_record(tmp_path, point):
    kill_batch = 2 if point.startswith("seg") else 3
    p = _child(tmp_path, "Fed", 0, 6, 3, 2, point, kill_batch)
    assert p.returncode == -9, (p.returncode, p.stdout, p.stderr)
    acked = _acked(p.stdout)
    assert acked == list(range(kill_batch))
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.reader.connect()
    seen = W.keys_of_frame(m.read_data())
    assert len(seen) == len(set(seen)), "duplicates after crash"
    per_batch = W.batches_in(seen, 3)
    full = 3 * len(W.TYPES)
    assert all(n == full for n in per_batch.values()), f"partial batch visible: {per_batch}"
    assert set(acked) <= set(per_batch) <= set(acked) | {kill_batch}
    expected = {W.key_of_record(r) for k in per_batch for r in W.make_batch("Fed", k, 3)}
    assert set(seen) == expected, "recovered values differ from what was written"
    # a new writer process continues, cleans up and consolidates
    p2 = _child(tmp_path, "Fed", 10, 3, 3, 2, "none", -1)
    assert "DONE" in p2.stdout, p2.stderr
    final = W.keys_of_frame(m.read_data())
    assert sorted(final) == sorted(expected | {W.key_of_record(r) for k in (10, 11, 12)
                                              for r in W.make_batch("Fed", k, 3)})
    leftovers = [x.name for x in (tmp_path / "A").rglob("*") if ".tmp-" in x.name]
    assert not leftovers and not (tmp_path / "A" / "Fed.h5.segments").exists()


def test_factory_overrides_do_not_leak(tmp_path):
    defaults = dict(cosim_toolbox.h5_data_db)
    first = create_timeseries_manager("hdf5", "one", location=str(tmp_path), compression=None, max_segments=3)
    second = create_timeseries_manager("hdf5", "two")
    assert (first.location, first.helper.compression, first.helper.max_segments) == (tmp_path, None, 3)
    assert str(second.location) == str(Path(defaults["location"]))
    assert (second.helper.compression, second.helper.max_segments) == (defaults["compression"], defaults["max_segments"])
    assert cosim_toolbox.h5_data_db == defaults


# ------------------------------------------------------------------ review finding regressions
_SETUP = """
import sys, logging; logging.disable(logging.CRITICAL)
import hdf5_workload as W
from cosim_toolbox.dbms.hdf5_timeseries import HDF5TimeSeriesManager
loc, consolidated_batches, segment_batches = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
m = HDF5TimeSeriesManager(location=loc, analysis_name="A", max_segments=1000); m.connect()
for k in range(consolidated_batches + segment_batches):
    assert m.write_records(W.make_batch("Fed", k, 2))
    if k + 1 == consolidated_batches:
        assert m.consolidate()
m.writer._touched.clear()  # exit with segments left unconsolidated
"""
_PAUSED_READER = """
import sys, os, time, logging; logging.disable(logging.CRITICAL)
import cosim_toolbox.dbms.hdf5_timeseries as M
loc, barrier = sys.argv[1], sys.argv[2]
orig, state = M.HDF5Helper.live_segments, {"paused": False}
def paused(self, federate, through):
    if not state["paused"]:
        state["paused"] = True
        open(barrier + ".paused", "w").close()
        while not os.path.exists(barrier + ".go"):
            time.sleep(0.005)
    return orig(self, federate, through)
M.HDF5Helper.live_segments = paused
m = M.HDF5TimeSeriesManager(location=loc, analysis_name="A"); m.reader.connect()
print(len(m.read_data()))
"""
_ACTOR = """
import sys, logging; logging.disable(logging.CRITICAL)
from cosim_toolbox.dbms.hdf5_timeseries import HDF5TimeSeriesManager
m = HDF5TimeSeriesManager(location=sys.argv[1], analysis_name="A", lock_timeout=30); m.connect()
print(m.consolidate() if sys.argv[2] == "consolidate" else m.delete_federate_data("Fed"))
"""


@pytest.mark.skipif(not POSIX, reason="multi-process lock test")
@pytest.mark.parametrize("consolidated,segments,action", [(0, 3, "consolidate"), (2, 3, "consolidate"),
                                                          (2, 3, "delete")],
                         ids=["first-file-creation", "consolidation-removes-segment-dir", "concurrent-deletion"])
def test_reader_snapshot_cannot_omit_segments_during_consolidation(tmp_path, consolidated, segments, action):
    """Review finding 1: a reader paused between opening the consolidated file and listing segments
    must not return stale data while another process consolidates or deletes the federate."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(TESTS_DIR.parent), str(TESTS_DIR)]))
    run = lambda code, *a, **k: subprocess.Popen([sys.executable, "-c", code, str(tmp_path), *a], env=env,
                                                 stdout=subprocess.PIPE, text=True, **k)
    assert run(_SETUP, str(consolidated), str(segments)).wait(timeout=60) == 0
    expected = (consolidated + segments) * 2 * len(W.TYPES)
    barrier = str(tmp_path / "barrier")
    reader = run(_PAUSED_READER, barrier)
    deadline = time.monotonic() + 30
    while not os.path.exists(barrier + ".paused"):
        assert time.monotonic() < deadline
        time.sleep(0.005)
    actor = run(_ACTOR, action)
    with pytest.raises(subprocess.TimeoutExpired):
        actor.wait(timeout=1.0)  # the consolidation/deletion must wait for the reader's snapshot
    Path(barrier + ".go").touch()
    assert int(reader.communicate(timeout=60)[0]) == expected
    assert actor.communicate(timeout=60)[0].strip() == "True"
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.reader.connect()
    assert len(m.read_data()) == (expected if action == "consolidate" else 0)


def test_reading_a_copy_without_lock_files_creates_nothing(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "src"), analysis_name="A"); m.connect()
    assert m.write_records([rec(fed="F1"), rec(fed="F2")])
    assert m.backup_analysis(str(tmp_path / "copy" / "A"))
    before = sorted(p.name for p in (tmp_path / "copy" / "A").iterdir())
    c = HDF5TimeSeriesManager(location=str(tmp_path / "copy"), analysis_name="A"); c.reader.connect()
    assert len(c.read_data()) == 2 and c.list_federates() == ["F1", "F2"]
    assert sorted(p.name for p in (tmp_path / "copy" / "A").iterdir()) == before == ["F1.h5", "F2.h5"]


def test_direct_write_does_not_overtake_pending_batch(tmp_path, monkeypatch):
    """Review finding 2: a direct write must not commit a higher sequence number while an
    earlier buffered batch is pending, or the retry of that batch would be skipped."""
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    m.add_record(rec(0, 1.0, fed="F1")); m.add_record(rec(0, 1.0, fed="F2"))
    _fail_once(monkeypatch, "_commit_segment", predicate=lambda helper, fed, *a: fed == "F2")
    assert not m.flush()                                  # F1 committed, F2 pending
    assert m.write_records([rec(1, 2.0, fed="F2")])       # commits the pending batch first
    assert m.flush()
    df = m.read_data()
    assert sorted(zip(df["federate"], df["sim_time"])) == [("F1", 0.0), ("F2", 0.0), ("F2", 1.0)]


def test_direct_write_refused_while_pending_batch_cannot_commit(tmp_path, monkeypatch):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A"); m.connect()
    m.add_record(rec(0, 1.0, fed="F2"))
    orig = M._commit_segment
    monkeypatch.setattr(M, "_commit_segment", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    assert not m.flush() and not m.write_records([rec(1, 2.0, fed="F2")])
    monkeypatch.setattr(M, "_commit_segment", orig)
    assert m.write_records([rec(1, 2.0, fed="F2")]) and m.buffer_size == 0
    assert sorted(m.read_data()["sim_time"]) == [0.0, 1.0]


class _BrokenTZ(tzinfo):
    def utcoffset(self, dt):
        raise RuntimeError("broken tzinfo")


BAD_RECORDS = [
    ("huge int as double", lambda: rec(1, 10**400, dt="hdt_double")),
    ("huge int in vector", lambda: rec(1, [10**400], dt="hdt_vector")),
    ("huge int as complex", lambda: rec(1, 10**400, dt="hdt_complex")),
    ("huge int in complex vector", lambda: rec(1, [10**400], dt="hdt_complex_vector")),
    ("huge int as sim_time", lambda: rec(10**400)),
    ("overflowing numeric string", lambda: rec(1, "1e400", dt="hdt_double")),
    ("overflowing complex string", lambda: rec(1, "1e400j", dt="hdt_complex")),
    ("huge integer string", lambda: rec(1, "9" * 5000, dt="hdt_integer")),
    ("extended precision beyond float64 range", lambda: rec(1, np.finfo(np.longdouble).max, dt="hdt_double")),
    ("timestamp beyond 2262", lambda: rec(1, rt=datetime(9999, 1, 1, tzinfo=UTC))),
    ("broken tzinfo", lambda: rec(1, rt=datetime(2026, 1, 1, tzinfo=_BrokenTZ()))),
    ("not a TSRecord", lambda: {"federate": "Battery"}),
    ("None", lambda: None),
    ("federate is not a string", lambda: rec(1, fed=5)),
]


@pytest.mark.parametrize("label,make", BAD_RECORDS, ids=[b[0] for b in BAD_RECORDS])
def test_bad_records_are_rejected_and_accounted_never_dropped_silently(mgr, label, make):
    """Review finding 3: a record whose conversion raises must not discard the buffer."""
    if label == "extended precision beyond float64 range":
        if np.finfo(np.longdouble).max <= np.finfo(np.float64).max:
            pytest.skip("platform long double has no wider range than float64")
    bad = make()
    mgr.add_record(rec(0, 1.0)); mgr.add_record(bad); mgr.add_record(rec(2, 3.0))
    assert mgr.flush() is False
    assert [r for r, _ in mgr.writer.rejected] == [bad] and mgr.buffer_size == 0
    assert mgr.read_data()["sim_time"].tolist() == [0.0, 2.0]
    assert not mgr.write_records([rec(5, 1.0), bad]) and len(mgr.read_data()) == 2


def test_unexpected_preparation_error_keeps_buffer(mgr, monkeypatch):
    mgr.add_record(rec(0, 1.0))
    monkeypatch.setattr(M.HDF5TimeSeriesWriter, "_prepare", lambda *a, **k: (_ for _ in ()).throw(MemoryError()))
    with pytest.raises(MemoryError):
        mgr.flush()
    assert mgr.buffer_size == 1, "records must not be discarded when preparation itself fails"
    monkeypatch.undo()
    assert mgr.flush() and len(mgr.read_data()) == 1


# ------------------------------------------------------------------ final review findings
def _recording(monkeypatch, fail=lambda kind, path: False):
    """Record every fsync/unlink in order; raise OSError from fsync when fail(kind, path) is true."""
    calls = []
    for kind in ("_fsync_path", "_fsync_dir"):
        orig = getattr(M, kind)

        def wrapper(path, kind=kind, orig=orig):
            calls.append((kind, str(path)))
            if fail(kind, Path(path)):
                raise OSError(f"injected {kind} failure")
            return orig(path)

        monkeypatch.setattr(M, kind, wrapper)
    orig_unlink = Path.unlink

    def unlink(self, *a, **k):
        calls.append(("unlink", str(self)))
        return orig_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink)
    return calls


def test_failed_segment_dir_fsync_is_not_acknowledged_on_retry(mgr, monkeypatch):
    """Final review finding 1: the retry must complete the fsync the failed attempt skipped."""
    state = {"fail": 1}

    def fail(kind, path):
        if kind == "_fsync_dir" and path.name.endswith(".segments") and state["fail"]:
            state["fail"] -= 1
            return True
        return False

    calls = _recording(monkeypatch, fail)
    mgr.add_record(rec(0, 1.0))
    assert not mgr.flush() and mgr.buffer_size == 1   # published, but its directory fsync failed
    before = len(calls)
    assert mgr.flush() and mgr.buffer_size == 0
    assert any(k == "_fsync_dir" and c.endswith(".segments") for k, c in calls[before:])
    assert len(mgr.read_data()) == 1


@pytest.mark.parametrize("target", ["segment file", "segment dir", "analysis dir", "location dir"])
def test_persistent_fsync_failure_is_never_acknowledged(tmp_path, monkeypatch, target):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "store"), analysis_name="A"); m.connect()
    picks = {"segment file": lambda k, p: k == "_fsync_path" and ".segments" in str(p),
             "segment dir": lambda k, p: k == "_fsync_dir" and p.name.endswith(".segments"),
             "analysis dir": lambda k, p: k == "_fsync_dir" and p == tmp_path / "store" / "A",
             "location dir": lambda k, p: k == "_fsync_dir" and p == tmp_path / "store"}
    _recording(monkeypatch, picks[target])
    m.add_record(rec(0, 1.0))
    for _ in range(3):
        assert not m.flush() and m.buffer_size == 1
    monkeypatch.undo()
    assert m.flush() and m.buffer_size == 0 and len(m.read_data()) == 1


def test_new_segment_directory_entry_synced_on_retry(mgr, tmp_path, monkeypatch):
    """A failed fsync of the parent of a newly created segment directory must be redone on retry."""
    state = {"fail": 1}

    def fail(kind, path):
        if kind == "_fsync_dir" and path == tmp_path / "A" and state["fail"]:
            state["fail"] -= 1
            return True
        return False

    calls = _recording(monkeypatch, fail)
    mgr.add_record(rec(0, 1.0))
    assert not mgr.flush()
    before = len(calls)
    assert mgr.flush()
    assert ("_fsync_dir", str(tmp_path / "A")) in calls[before:]


def test_consolidation_fsync_failure_keeps_segments_until_durable(tmp_path, monkeypatch):
    """If the directory fsync after replacing the consolidated file fails, the segments it covers
    are deleted only after the consolidated file and its directory have been fsynced."""
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=2); m.connect()
    analysis = tmp_path / "A"
    state = {"armed": False, "fail": 1}

    def fail(kind, path):
        if state["armed"] and kind == "_fsync_dir" and path == analysis and state["fail"]:
            state["fail"] -= 1
            return True
        return False

    calls = _recording(monkeypatch, fail)
    assert m.write_records([rec(0, 1.0)])
    state["armed"] = True
    assert m.write_records([rec(1, 2.0)])  # segment durable; consolidation's final fsync fails (logged)
    covered = sorted((analysis / "Battery.h5.segments").glob("*.h5"))
    assert len(covered) == 2 and (analysis / "Battery.h5").exists()
    assert sorted(m.read_data()["sim_time"]) == [0.0, 1.0], "no duplicates while segments and file coexist"
    before = len(calls)
    assert m.write_records([rec(2, 3.0)])  # removes the covered segments, after syncing
    later = calls[before:]
    sync_at = later.index(("_fsync_path", str(analysis / "Battery.h5")))
    for seg in covered:
        assert sync_at < later.index(("unlink", str(seg)))
    assert sorted(m.read_data()["sim_time"]) == [0.0, 1.0, 2.0]


def test_consolidation_segments_kept_while_fsync_keeps_failing(tmp_path, monkeypatch):
    m = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="A", max_segments=2); m.connect()
    assert m.write_records([rec(0, 1.0)])
    _recording(monkeypatch, lambda k, p: k == "_fsync_path" and p == tmp_path / "A" / "Battery.h5")
    for t in range(1, 5):
        m.write_records([rec(t, 1.0)])
    monkeypatch.undo()
    assert sorted(m.read_data()["sim_time"]) == [0.0, 1.0, 2.0, 3.0, 4.0]


@pytest.mark.parametrize("consolidate", [False, True], ids=["segments", "consolidated"])
def test_mixed_type_read_preserves_complex_nan(mgr, consolidate):
    """Final review finding 2: pandas 2.x concat dropped the imaginary part of complex(nan, 1)."""
    assert mgr.write_records([rec(0, math.nan, dt="hdt_double"), rec(1, [math.nan], dt="hdt_vector"),
                              rec(2, complex(math.nan, 1), dt="hdt_complex"),
                              rec(3, "m", dt="hdt_endpoint", receiving_federate=None, receiving_endpoint="X")])
    if consolidate:
        assert mgr.consolidate()
    df = mgr.read_data()
    v = df["data_value"]
    assert math.isnan(v[0]) and math.isnan(v[1][0])
    assert isinstance(v[2], complex) and math.isnan(v[2].real) and v[2].imag == 1
    assert df["receiving_federate"][3] is None and df["receiving_endpoint"][3] == "X"
    assert all(isinstance(x, float) and math.isnan(x) for x in df["receiving_federate"][:3])
    assert str(df["data_value"].dtype) == "object"


@pytest.mark.parametrize("ts,expected", [
    (pd.Timestamp("2026-01-01T00:00:00.123456789Z"), 1767225600123456789),
    (pd.Timestamp("2026-01-01T00:00:00.123456789"), 1767225600123456789),           # naive: UTC
    (pd.Timestamp("2025-12-31T18:00:00.000000001", tz="America/Chicago"), 1767225600000000001),
    (pd.Timestamp("2262-04-11T23:47:16.854775807Z"), 2**63 - 1),
])
def test_pandas_timestamp_nanoseconds_preserved(mgr, ts, expected):
    """Final review finding 3: pandas.Timestamp nanoseconds were truncated to microseconds."""
    assert M._to_ns(ts) == expected
    assert mgr.write_records([rec(rt=ts)])
    assert mgr.read_data()["real_time"].iloc[0].value == expected


def test_out_of_range_pandas_timestamp_rejected(mgr):
    ts = pd.Timestamp(datetime(3000, 1, 1)).as_unit("s")  # representable by pandas, not in int64 nanoseconds
    assert not mgr.write_records([rec(rt=ts)]) and mgr.read_data().empty


def _two_federates(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "src"), analysis_name="A"); m.connect()
    assert m.write_records([rec(fed="F1"), rec(fed="F2")])
    return m


def test_repeated_backup_reflects_current_federates(tmp_path):
    """Final review finding 4: a second backup to the same destination kept a deleted federate."""
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    assert m.backup_analysis(str(dest)) and sorted(p.name for p in dest.iterdir()) == ["F1.h5", "F2.h5"]
    assert m.delete_federate_data("F2") and m.write_records([rec(1, fed="F1")])
    assert m.backup_analysis(str(dest)) and sorted(p.name for p in dest.iterdir()) == ["F1.h5"]
    b = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="bak"); b.reader.connect()
    assert b.read_data().equals(m.read_data())
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".bak")] == []


@pytest.mark.parametrize("setup", ["unrelated file", "subdirectory", "other analysis", "not a directory",
                                   "inside source", "source itself"])
def test_backup_refuses_destinations_with_other_content(tmp_path, setup):
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    if setup == "unrelated file":
        dest.mkdir(); (dest / "notes.txt").write_text("keep")
    elif setup == "subdirectory":
        dest.mkdir(); (dest / "results").mkdir()
    elif setup == "other analysis":
        other = HDF5TimeSeriesManager(location=str(tmp_path / "o"), analysis_name="B"); other.connect()
        assert other.write_records([rec(fed="F1")]) and other.backup_analysis(str(dest))
    elif setup == "not a directory":
        dest.write_text("keep")
    elif setup == "inside source":
        dest = tmp_path / "src" / "A" / "bak"
    else:
        dest = tmp_path / "src" / "A"
    snapshot = sorted((p.relative_to(tmp_path), p.read_bytes() if p.is_file() else None)
                      for p in tmp_path.rglob("*"))
    assert not m.backup_analysis(str(dest))
    assert sorted((p.relative_to(tmp_path), p.read_bytes() if p.is_file() else None)
                  for p in tmp_path.rglob("*")) == snapshot, "nothing may be changed or deleted"


def test_failed_backup_keeps_previous_backup(tmp_path, monkeypatch):
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    assert m.backup_analysis(str(dest))
    previous = {p.name: p.read_bytes() for p in dest.iterdir()}
    assert m.write_records([rec(1, fed="F1"), rec(1, fed="F2")])
    _fail_once(monkeypatch, "copyfile", M.shutil, predicate=lambda src, dst: Path(dst).name == "F2.h5")
    assert not m.backup_analysis(str(dest))
    assert {p.name: p.read_bytes() for p in dest.iterdir()} == previous
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".bak")] == []
    assert m.backup_analysis(str(dest))
    b = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="bak"); b.reader.connect()
    assert b.read_data().equals(m.read_data()) and len(b.read_data()) == 4


def _tree(root):
    return sorted((str(p.relative_to(root)), p.read_bytes() if p.is_file() else None) for p in root.rglob("*"))


def test_backup_after_all_federates_deleted_empties_destination(tmp_path):
    """Review finding B1: with no federates left, backup returned True and kept the old files."""
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    assert m.backup_analysis(str(dest))
    assert m.delete_federate_data("F1") and m.delete_federate_data("F2") and m.read_data().empty
    assert m.backup_analysis(str(dest))
    assert dest.is_dir() and list(dest.iterdir()) == []
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".bak")] == []
    b = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="bak"); b.reader.connect()
    assert b.read_data().empty


def test_empty_analysis_backup_still_validates_destination(tmp_path):
    m = HDF5TimeSeriesManager(location=str(tmp_path / "src"), analysis_name="A"); m.connect()
    dest = tmp_path / "bak"
    dest.mkdir(); (dest / "notes.txt").write_text("keep")
    before = _tree(tmp_path)
    assert not m.backup_analysis(str(dest)) and _tree(tmp_path) == before
    assert m.backup_analysis(str(tmp_path / "new")) and not (tmp_path / "new").exists()


@pytest.mark.parametrize("had_previous", [True, False])
def test_backup_parent_fsync_failure_restores_previous_state(tmp_path, monkeypatch, had_previous):
    """Review finding B2: a failed destination-parent fsync returned False after publishing the new
    backup and left the previous one in a hidden directory."""
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    if had_previous:
        assert m.backup_analysis(str(dest))
        assert m.delete_federate_data("F2") and m.write_records([rec(1, fed="F1")])
    before = _tree(tmp_path / "bak") if had_previous else None
    state = {"fail": 1}

    def fail(kind, path):
        if kind == "_fsync_dir" and path == tmp_path and state["fail"]:
            state["fail"] -= 1
            return True
    _recording(monkeypatch, fail)
    assert not m.backup_analysis(str(dest))
    if had_previous:
        assert _tree(dest) == before, "False must mean the destination is unchanged"
    else:
        assert not dest.exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".bak")] == []
    expected = ["F1.h5"] if had_previous else ["F1.h5", "F2.h5"]
    assert m.backup_analysis(str(dest)) and sorted(p.name for p in dest.iterdir()) == expected
    b = HDF5TimeSeriesManager(location=str(tmp_path), analysis_name="bak"); b.reader.connect()
    assert b.read_data().equals(m.read_data())


def test_backup_rollback_keeps_copies_when_restore_is_not_durable(tmp_path, monkeypatch):
    """If the rollback cannot be made durable either, nothing is deleted: both copies stay."""
    m = _two_federates(tmp_path)
    dest = tmp_path / "bak"
    assert m.backup_analysis(str(dest))
    before = _tree(dest)
    assert m.delete_federate_data("F2")
    _recording(monkeypatch, lambda k, p: k == "_fsync_dir" and p == tmp_path)
    assert not m.backup_analysis(str(dest))
    assert _tree(dest) == before
    hidden = [p for p in tmp_path.iterdir() if p.name.startswith(".bak")]
    assert len(hidden) == 1 and sorted(p.name for p in hidden[0].iterdir()) == ["F1.h5"]
