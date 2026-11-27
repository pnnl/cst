"""
Deterministic workload and crash-injection child process for the HDF5 backend tests.

Not collected by pytest. Used by test_hdf5_timeseries.py and by the longer
randomized experiments. Crash points are injected from outside by wrapping
functions of cosim_toolbox.dbms.hdf5_timeseries in the child process only; the
production module contains no test hooks.

Child usage:
    python hdf5_workload.py <location> <analysis> <federate[,federate...]> <first_batch> <n_batches>
                            <batch_size> <max_segments|default> <kill_point|none> <kill_batch>
                            [<random_kill_after_s>]
Each flush holds one batch for every listed federate. Prints "ACK <batch>" after every flush
that returned True. "default" uses the production defaults for every option.
"""

import os
import shutil
import signal
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

T0 = datetime(2026, 1, 1, tzinfo=UTC)
TYPES = ("hdt_boolean", "hdt_integer", "hdt_double", "hdt_complex", "hdt_string",
         "hdt_vector", "hdt_complex_vector", "hdt_endpoint")


def make_value(data_type: str, k: int, i: int):
    x = k * 100_003 + i
    return {
        "hdt_boolean": x % 2 == 0,
        "hdt_integer": (x * 7919) % (2**62) - 2**61,
        "hdt_double": x / 7.0 - 1e3,
        "hdt_complex": complex(x / 3.0, -x / 11.0),
        "hdt_string": f"v{x}-Δ€",
        "hdt_vector": [float(x + j) / 5.0 for j in range(x % 4)],
        "hdt_complex_vector": [complex(x, j) for j in range(x % 3 + 1)],
        "hdt_endpoint": bytes([x % 256, 0, 255]) if x % 2 else f"msg{x}",
    }[data_type]


def make_batch(federate: str, k: int, n: int) -> list:
    """n records per data type for batch k; sim_time encodes (k, i) uniquely."""
    from cosim_toolbox.dbms.time_series_record import TSRecord

    records = []
    for i in range(n):
        st = float(k * 1_000_000 + i)
        rt = T0 + timedelta(seconds=st, microseconds=i)
        for dt in TYPES:
            kw = {"receiving_federate": "R", "receiving_endpoint": "R/in"} if dt == "hdt_endpoint" else {}
            records.append(TSRecord(rt, st, "scen", federate, f"{federate}/{dt}", make_value(dt, k, i),
                                    data_type=dt, **kw))
    return records


def _ns(dt) -> int:
    delta = dt - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


def key_of_record(r) -> tuple:
    """Every stored field of a record: (federate, data_name, scenario, sim_time, real_time ns,
    receiving_federate, receiving_endpoint, repr(value))."""
    rf, rep = (r.receiving_federate, r.receiving_endpoint) if r.data_type == "hdt_endpoint" else (None, None)
    return (r.federate, r.data_name, r.scenario, float(r.sim_time), _ns(r.real_time), rf, rep, repr(r.data_value))


def keys_of_frame(df) -> list[tuple]:
    if df.empty:
        return []
    def text(series):
        return [x if isinstance(x, str) else None for x in series] if series is not None else [None] * len(df)
    rf = text(df.get("receiving_federate"))
    rep = text(df.get("receiving_endpoint"))
    return [(f, n, s, float(t), int(rt.value), a, b, repr(v)) for f, n, s, t, rt, a, b, v in
            zip(df["federate"], df["data_name"], df["scenario"], df["sim_time"], df["real_time"], rf, rep,
                df["data_value"])]


def batches_in(keys, n: int) -> dict[int, int]:
    """Number of distinct records seen per batch index."""
    out: dict[int, int] = {}
    for key in keys:
        k = int(key[3]) // 1_000_000
        out[k] = out.get(k, 0) + 1
    return out


def _kill():
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGKILL)


def install_kill(point: str, analysis_dir: Path) -> dict:
    """Wrap one function so the process SIGKILLs itself at a commit stage once ARMED."""
    import cosim_toolbox.dbms.hdf5_timeseries as M

    state = {"armed": False, "calls": 0}
    seg = lambda p: ".segments" in str(p)
    top = lambda p: Path(p).parent == analysis_dir

    def wrap(obj, attr, when, pred=lambda *a, **k: True, nth=1):
        orig = getattr(obj, attr)

        def wrapper(*a, **k):
            hit = state["armed"] and pred(*a, **k)
            if hit:
                state["calls"] += 1
                hit = state["calls"] == nth
            if hit and when == "before":
                _kill()
            result = orig(*a, **k)
            if hit and when == "after":
                _kill()
            return result

        setattr(obj, attr, wrapper)

    points = {
        "seg_mid_write": lambda: wrap(M, "_write_rows", "before", lambda ds, *a: seg(ds.file.filename), 3),
        "seg_before_publish": lambda: wrap(M.HDF5Helper, "publish", "before", lambda self, tmp, final: seg(final)),
        "seg_after_fsync": lambda: wrap(M, "_fsync_path", "after", lambda p: seg(p)),
        "seg_after_replace": lambda: wrap(os, "replace", "after", lambda src, dst: seg(dst)),
        "seg_after_dir_fsync": lambda: wrap(M, "_fsync_dir", "after", lambda p: seg(p)),
        "con_after_copy": lambda: wrap(shutil, "copyfile", "after", lambda src, dst: top(dst)),
        "con_mid_append": lambda: wrap(M, "_append_columns", "before", nth=3),
        "con_before_publish": lambda: wrap(M.HDF5Helper, "publish", "before",
                                           lambda self, tmp, final: top(final)),
        "con_after_fsync": lambda: wrap(M, "_fsync_path", "after", lambda p: top(p)),
        "con_after_replace": lambda: wrap(os, "replace", "after", lambda src, dst: top(dst)),
        "con_mid_cleanup": lambda: wrap(Path, "unlink", "after",
                                        lambda self, *a, **k: seg(self) and ".tmp-" not in self.name, 1),
    }
    if point != "none":
        points[point]()
    return state


SEGMENT_POINTS = ("seg_mid_write", "seg_before_publish", "seg_after_fsync", "seg_after_replace",
                  "seg_after_dir_fsync")
CONSOLIDATION_POINTS = ("con_after_copy", "con_mid_append", "con_before_publish", "con_after_fsync",
                        "con_after_replace", "con_mid_cleanup")


def child_main(argv: list[str]) -> int:
    import logging
    import threading

    logging.disable(logging.CRITICAL)
    loc, analysis, federates = argv[0], argv[1], argv[2].split(",")
    first, count, size = (int(x) for x in argv[3:6])
    options = {} if argv[6] == "default" else {"max_segments": int(argv[6])}
    point, kill_batch = argv[7], int(argv[8])
    from cosim_toolbox.dbms.hdf5_timeseries import HDF5TimeSeriesManager

    state = install_kill(point, Path(loc) / analysis)
    if len(argv) > 9:  # random-time kill
        threading.Timer(float(argv[9]), _kill).start()
    mgr = HDF5TimeSeriesManager(location=loc, analysis_name=analysis, **options)
    mgr.connect()
    for k in range(first, first + count):
        for federate in federates:
            for r in make_batch(federate, k, size):
                mgr.add_record(r)
        state["armed"] = k == kill_batch
        if mgr.flush():
            print(f"ACK {k}", flush=True)
        else:
            print(f"FAIL {k}", flush=True)
            return 3
    state["armed"] = False
    mgr.disconnect()
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(child_main(sys.argv[1:]))
