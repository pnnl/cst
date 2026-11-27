"""
HDF5 file-based time-series data management for CoSim Toolbox.

All data of one federate, of every data type, is kept in one HDF5 file,
following the composition-based Helper / Writer / Reader / Manager design of
the CSV and Parquet backends.

Storage layout (``<location>/<analysis_name>/``)::

    <federate>.h5             consolidated, user-facing file for the federate
    <federate>.h5.segments/   committed batches not yet consolidated
    <federate>.h5.lock        interprocess lock file (never deleted)

``<federate>`` is the federate name, percent-encoded so that names containing
path separators (for example ``Battery/EV1``) stay inside the analysis
directory and decode back to the original name.

Commit protocol. A published HDF5 file is never modified in place. Each flush
writes the batch for a federate to a new segment file under a temporary name,
closes and re-validates it, fsyncs it and atomically renames it into place.
Segments are folded into ``<federate>.h5`` by building a complete new copy under
a temporary name and atomically replacing the old file (copy-on-write), when
``max_segments`` segments are pending and on ``disconnect()``. Writers and
readers of a federate coordinate through an OS lock on the ``.lock`` file;
readers hold it only while opening the files of their snapshot. Commits are per
federate: a batch spanning several federates is not atomic across them. See
``docs/TimeSeriesData.md`` for the tested guarantees, supported platforms and
limitations.

@author Nikhil Reddy Donapati (developed with AI assistance)
"""

from __future__ import annotations

import errno
import logging
import os
import re
import shutil
import stat
import sys
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

from .abstractions import (
    TimeSeriesManager,
    TimeSeriesReader,
    TimeSeriesWriter,
    TSRecord,
)
from .validation import ValidationError, safe_name_log, validate_name

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows: connect() raises HDF5StoreError
    fcntl = None

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1"
BACKEND_ID = "cosim_toolbox.hdf5"

# --------------------------------------------------------------------------------------
# Data types
# --------------------------------------------------------------------------------------
DATA_TYPES = (
    "hdt_boolean",
    "hdt_integer",
    "hdt_double",
    "hdt_complex",
    "hdt_string",
    "hdt_vector",
    "hdt_complex_vector",
    "hdt_endpoint",
)
# Federate builds table names as f"hdt_{type.lower()}" from the HELICS configuration.
# HELICS 3.6.1 reports these alternate spellings as the same types; CST itself
# uses "complex vector" (with a space) in Federate.get_data_from_federation.
TYPE_ALIASES = {
    "hdt_float": "hdt_double",
    "hdt_int": "hdt_integer",
    "hdt_int64": "hdt_integer",
    "hdt_bool": "hdt_boolean",
    "hdt_double_vector": "hdt_vector",
    "hdt_complex vector": "hdt_complex_vector",
}

_STR = h5py.string_dtype("utf-8")
_VALUE_DTYPES = {
    "hdt_boolean": np.dtype(np.bool_),
    "hdt_integer": np.dtype(np.int64),
    "hdt_double": np.dtype(np.float64),
    "hdt_complex": np.dtype(np.complex128),
    "hdt_string": _STR,
    "hdt_vector": h5py.vlen_dtype(np.float64),
    "hdt_complex_vector": h5py.vlen_dtype(np.complex128),
    "hdt_endpoint": h5py.vlen_dtype(np.uint8),
}
_BASE_COLUMNS = {
    "real_time": np.dtype(np.int64),
    "sim_time": np.dtype(np.float64),
    "scenario": _STR,
    "data_name": _STR,
}
# null_mask: bit 0 -> receiving_federate is None, bit 1 -> receiving_endpoint is None
# value_kind: 0 -> payload was str (UTF-8), 1 -> payload was bytes
_ENDPOINT_COLUMNS = {
    "receiving_federate": _STR,
    "receiving_endpoint": _STR,
    "null_mask": np.dtype(np.uint8),
    "value_kind": np.dtype(np.uint8),
}
_WRITERS_DTYPE = np.dtype([("writer_id", "S32"), ("batch_seq", np.int64)])
_WRITERS = "_cst_writers"

_I64_MIN, _I64_MAX = -(2**63), 2**63 - 1
_F64_EXACT_INT = 2**53
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
# pandas represents datetime64[ns] in [int64 min + 1, int64 max]; int64 min is NaT.
_NS_MIN, _NS_MAX = _I64_MIN + 1, _I64_MAX


class HDF5StoreError(OSError):
    """Raised when HDF5 time-series data cannot be read or written safely."""


class UnsupportedDataTypeError(ValidationError):
    """Raised for data types the HDF5 backend does not store."""


def canonical_data_type(data_type: str | None) -> str:
    """Return the canonical CST data type for a data type or alias.

    Args:
        data_type (str | None): data type such as "hdt_double" or an alias
            such as "hdt_float"

    Raises:
        UnsupportedDataTypeError: if the type is not one of DATA_TYPES or an alias

    Returns:
        str: one of DATA_TYPES
    """
    if not isinstance(data_type, str):
        raise UnsupportedDataTypeError(f"data_type must be a string, got {data_type!r}")
    dt = data_type.strip().lower()
    dt = TYPE_ALIASES.get(dt, dt)
    if dt not in DATA_TYPES:
        raise UnsupportedDataTypeError(
            f"data type '{safe_name_log(data_type)}' is not supported by the HDF5 backend; "
            f"supported: {', '.join(DATA_TYPES)}"
        )
    return dt


def _columns(data_type: str) -> dict[str, np.dtype]:
    cols = dict(_BASE_COLUMNS)
    if data_type == "hdt_endpoint":
        cols.update(_ENDPOINT_COLUMNS)
    cols["data_value"] = _VALUE_DTYPES[data_type]
    return cols


# --------------------------------------------------------------------------------------
# Lossless value conversion
# --------------------------------------------------------------------------------------
def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be str, got {type(value).__name__}")
    if "\x00" in value:
        raise ValidationError(f"{field} contains an embedded NUL character")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as e:
        raise ValidationError(f"{field} is not valid Unicode text: {e.reason}") from None
    return value


def _exact_float(value: Any, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise ValidationError(f"{field}: bool is not a real number")
    if isinstance(value, (int, np.integer)):
        exact = int(value)
        if abs(exact) > _F64_EXACT_INT:
            try:
                if int(float(exact)) != exact:
                    raise OverflowError
            except OverflowError:
                raise ValidationError(f"{field}: integer {safe_name_log(str(exact))} "
                                      "is not exactly representable as float64") from None
        return float(exact)
    if isinstance(value, (float, np.floating)):
        result = float(value)
        lossy = isinstance(value, np.floating) and value.dtype.itemsize > 8 \
            and not np.isnan(value) and np.longdouble(result) != value
        if lossy:
            raise ValidationError(f"{field}: {value!r} would lose precision as float64")
        return result
    raise ValidationError(f"{field}: expected a real number, got {type(value).__name__}")


def _exact_complex(value: Any, field: str) -> complex:
    if isinstance(value, (complex, np.complexfloating)):
        result = complex(value)
        if isinstance(value, np.complexfloating) and value.dtype.itemsize > 16:
            for part, orig in ((result.real, value.real), (result.imag, value.imag)):
                if not np.isnan(orig) and np.longdouble(part) != orig:
                    raise ValidationError(f"{field}: {value!r} would lose precision as complex128")
        return result
    return complex(_exact_float(value, field), 0.0)


_PARSERS = {"hdt_integer": int, "hdt_double": float, "hdt_complex": complex}


def _parse_numeric_text(data_type: str, value: str, field: str) -> Any:
    """CST federates log the value given to a publication, which may be a string such as "(1+2j)";
    HELICS converts it for subscribers. Parse it the same way rather than drop the record."""
    text = value.strip()
    try:
        parsed = _PARSERS[data_type](text)
    except (ValueError, OverflowError):
        raise ValidationError(f"{field}: string {safe_name_log(value)!r} is not a valid {data_type[4:]}") from None
    if data_type != "hdt_integer" and "inf" not in text.lower() and np.isinf(parsed):
        raise ValidationError(f"{field}: string {safe_name_log(value)!r} overflows float64")
    return parsed


def _encode_value(data_type: str, value: Any) -> tuple[Any, int]:
    """Convert a value to its storage form; raise ValidationError rather than lose information."""
    field = f"{data_type} value"
    if isinstance(value, str) and data_type in _PARSERS:
        value = _parse_numeric_text(data_type, value, field)
    if data_type == "hdt_boolean":
        if not isinstance(value, (bool, np.bool_)):
            raise ValidationError(f"{field}: expected bool, got {type(value).__name__}")
        return bool(value), 0
    if data_type == "hdt_integer":
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValidationError(f"{field}: expected int, got {type(value).__name__}")
        if not _I64_MIN <= int(value) <= _I64_MAX:
            raise ValidationError(f"{field}: {value} is outside the int64 range")
        return int(value), 0
    if data_type == "hdt_double":
        return _exact_float(value, field), 0
    if data_type == "hdt_complex":
        return _exact_complex(value, field), 0
    if data_type == "hdt_string":
        return _text(value, field), 0
    if data_type in ("hdt_vector", "hdt_complex_vector"):
        if not isinstance(value, (list, tuple, np.ndarray)):
            raise ValidationError(f"{field}: expected a list, got {type(value).__name__}")
        if isinstance(value, np.ndarray) and value.ndim != 1:
            raise ValidationError(f"{field}: expected a 1-D array, got shape {value.shape}")
        if data_type == "hdt_vector":
            if isinstance(value, np.ndarray) and value.dtype in (np.float16, np.float32, np.float64):
                return value.astype(np.float64), 0
            return np.array([_exact_float(e, field) for e in value], dtype=np.float64), 0
        if isinstance(value, np.ndarray) and value.dtype in (np.complex64, np.complex128):
            return value.astype(np.complex128), 0
        return np.array([_exact_complex(e, field) for e in value], dtype=np.complex128), 0
    if data_type == "hdt_endpoint":
        if isinstance(value, (bytes, bytearray, memoryview)):
            return np.frombuffer(bytes(value), dtype=np.uint8), 1
        if isinstance(value, str):
            try:
                return np.frombuffer(value.encode("utf-8"), dtype=np.uint8), 0
            except UnicodeEncodeError as e:
                raise ValidationError(f"{field}: not valid Unicode text: {e.reason}") from None
        raise ValidationError(f"{field}: expected str or bytes, got {type(value).__name__}")
    raise UnsupportedDataTypeError(data_type)


def _decode_value(data_type: str, raw: Any, kind: int = 0) -> Any:
    if data_type == "hdt_boolean":
        return bool(raw)
    if data_type == "hdt_integer":
        return int(raw)
    if data_type == "hdt_double":
        return float(raw)
    if data_type == "hdt_complex":
        return complex(raw)
    if data_type == "hdt_string":
        return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    if data_type == "hdt_vector":
        return [float(x) for x in raw]
    if data_type == "hdt_complex_vector":
        return [complex(x) for x in raw]
    payload = bytes(np.asarray(raw, dtype=np.uint8))
    return payload if kind == 1 else payload.decode("utf-8")


def _to_ns(value: datetime) -> int:
    """Exact UTC nanoseconds since the Unix epoch (datetime: microseconds; pandas.Timestamp: nanoseconds).
    Naive values are taken as UTC, as in the Parquet backend."""
    if not isinstance(value, datetime):
        raise ValidationError(f"real_time must be a datetime, got {type(value).__name__}")
    if isinstance(value, pd.Timestamp):  # nanosecond resolution: use pandas' exact integer value
        try:
            ts = value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")
            ns = int(ts.as_unit("ns").value)
        except (OverflowError, ValueError) as e:
            raise ValidationError(f"real_time {value} is outside the representable range: {e}") from None
    else:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=UTC)
        delta = value - _EPOCH
        ns = (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000
    if not _NS_MIN <= ns <= _NS_MAX:
        raise ValidationError(
            f"real_time {value.isoformat()} is outside the representable range "
            "(1677-09-21 to 2262-04-11 UTC)"
        )
    return ns


# --------------------------------------------------------------------------------------
# Federate-name encoding (reversible, path-safe)
# --------------------------------------------------------------------------------------
_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-.")
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)}
_MAX_ENCODED = 200  # bytes; leaves room for suffixes within the common 255-byte name limit
_ESCAPE = re.compile(r"%[0-9A-F]{2}")


def encode_name(name: str) -> str:
    """Encode a federate name as a single, portable filename component.

    Every UTF-8 byte outside [A-Za-z0-9_.-] is written as %XX; so are a leading
    or trailing '.', and the first character of a Windows device name.
    decode_name(encode_name(x)) == x for every accepted name.
    """
    _text(name, "federate name")
    if not name:
        raise ValidationError("federate name cannot be empty")
    out = []
    for i, ch in enumerate(name):
        if ch in _SAFE and not (ch == "." and i in (0, len(name) - 1)):
            out.append(ch)
        else:
            out.extend(f"%{b:02X}" for b in ch.encode("utf-8"))
    encoded = "".join(out)
    if encoded.split(".")[0].upper() in _WIN_RESERVED:
        encoded = f"%{ord(encoded[0]):02X}{encoded[1:]}"
    if len(encoded) > _MAX_ENCODED:
        raise ValidationError(f"federate name too long once encoded: {safe_name_log(name)}")
    return encoded


def decode_name(encoded: str) -> str:
    """Inverse of encode_name."""
    if not set(_ESCAPE.sub("", encoded)) <= _SAFE:
        raise ValueError(f"not an encoded federate name: {encoded!r}")
    raw = bytearray()
    i = 0
    while i < len(encoded):
        if encoded[i] == "%":
            raw.append(int(encoded[i + 1:i + 3], 16))
            i += 3
        else:
            raw.extend(encoded[i].encode())
            i += 1
    return raw.decode("utf-8")


# --------------------------------------------------------------------------------------
# Filesystem primitives
# --------------------------------------------------------------------------------------
def _fsync_path(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        if sys.platform == "darwin" and hasattr(fcntl, "F_FULLFSYNC"):  # pragma: no cover
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
        else:
            os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    _fsync_path(path)  # POSIX: makes a rename or unlink in the directory durable


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise HDF5StoreError(errno.ELOOP, f"refusing to use symbolic link: {path}")


@contextmanager
def _lock(path: Path, timeout: float, create: bool = True):
    """Hold an exclusive flock() on a lock file whose inode never changes.

    Writers open the file read-write and create it; readers (create=False) open an
    existing file read-only and get FileNotFoundError if there is none. POSIX only.
    """
    _require_supported_platform()
    flags = (os.O_RDWR | os.O_CREAT if create else os.O_RDONLY) | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o644)
    except OSError as e:
        if e.errno == errno.ELOOP:
            raise HDF5StoreError(errno.ELOOP, f"refusing to use symbolic link: {path}") from None
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise HDF5StoreError(errno.EINVAL, f"lock path is not a regular file: {path}")
        deadline = time.monotonic() + timeout
        delay = 0.001
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise HDF5StoreError(errno.ETIMEDOUT, f"could not lock {path} within {timeout}s") from None
                time.sleep(delay)
                delay = min(delay * 2, 0.05)
        yield
    finally:
        os.close(fd)  # also releases the lock


# --------------------------------------------------------------------------------------
# Schema validation
# --------------------------------------------------------------------------------------
def _dtype_matches(actual: np.dtype, expected: np.dtype) -> bool:
    exp_str, act_str = h5py.check_string_dtype(expected), h5py.check_string_dtype(actual)
    if exp_str is not None or act_str is not None:
        return exp_str is not None and act_str is not None
    exp_vlen, act_vlen = h5py.check_vlen_dtype(expected), h5py.check_vlen_dtype(actual)
    if exp_vlen is not None or act_vlen is not None:
        return exp_vlen is not None and act_vlen is not None and np.dtype(exp_vlen) == np.dtype(act_vlen)
    return actual == expected


def _validate(f: h5py.File, federate: str, analysis: str | None, kind: str) -> dict[str, int]:
    """Check that a file is a complete CST HDF5 file of the expected kind for this federate
    (and, if analysis is given, written for that analysis).

    Returns:
        dict[str, int]: committed row count per data type
    """
    where = f.filename

    def fail(msg: str) -> None:
        raise HDF5StoreError(errno.EIO, f"{where}: {msg}")

    attrs = f.attrs
    for key in ("schema_version", "backend", "kind", "analysis", "federate"):
        if key not in attrs:
            fail(f"missing attribute '{key}'")
    if str(attrs["schema_version"]) != SCHEMA_VERSION:
        fail(f"unsupported schema_version {attrs['schema_version']!r}")
    if str(attrs["backend"]) != BACKEND_ID or str(attrs["kind"]) != kind:
        fail(f"not a CST HDF5 {kind} file")
    if str(attrs["federate"]) != federate:
        fail(f"belongs to federate {str(attrs['federate'])!r}, not {federate!r} "
             "(case-insensitive filename collision?)")
    if analysis is not None and str(attrs["analysis"]) != analysis:
        fail(f"belongs to analysis {str(attrs['analysis'])!r}, not {analysis!r}")
    if kind == "consolidated":
        if "segments_through" not in attrs:
            fail("missing attribute 'segments_through'")
        if _WRITERS not in f or f[_WRITERS].dtype != _WRITERS_DTYPE or f[_WRITERS].ndim != 1:
            fail(f"missing or invalid '{_WRITERS}' table")
    counts = {}
    for name, obj in f.items():
        if name == _WRITERS and kind == "consolidated":
            continue
        if name not in DATA_TYPES or not isinstance(obj, h5py.Group):
            fail(f"unexpected object '{name}'")
        if "nrows" not in obj.attrs:
            fail(f"group '{name}' has no 'nrows' attribute")
        nrows = int(obj.attrs["nrows"])
        expected = _columns(name)
        if set(obj.keys()) != set(expected):
            fail(f"group '{name}' has datasets {sorted(obj.keys())}, expected {sorted(expected)}")
        for col, dtype in expected.items():
            ds = obj[col]
            if ds.ndim != 1 or ds.shape[0] != nrows:
                fail(f"'{name}/{col}' has shape {ds.shape}, expected ({nrows},)")
            if not _dtype_matches(ds.dtype, dtype):
                fail(f"'{name}/{col}' has dtype {ds.dtype}, expected {dtype}")
        counts[name] = nrows
    return counts


def _require_supported_platform() -> None:
    if fcntl is None:
        raise HDF5StoreError(errno.ENOTSUP, "the HDF5 time-series backend requires POSIX file locking (fcntl) "
                                            f"and is not supported on {sys.platform}")


def check_analysis_name(name: str) -> None:
    """An analysis name must be a valid CST name and a single directory name."""
    validate_name(name, context="analysis")
    if "/" in name or "\\" in name:
        raise ValidationError(f"Analysis name must be a single directory name: {safe_name_log(name)}")


# --------------------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------------------
_SEGMENT = re.compile(r"^(\d{16})-([0-9a-f]{32})-(\d{16})\.h5$")


@dataclass(frozen=True)
class _Segment:
    path: Path
    seq: int
    writer_id: str
    batch_seq: int


class HDF5Helper:
    """Manages paths, locking, schema and value conversion for HDF5 time-series storage."""

    def __init__(
        self,
        location: str,
        analysis_name: str,
        *,
        compression: str | None = "gzip",
        compression_opts: int | None = 4,
        chunk_rows: int = 16384,
        max_segments: int = 32,
        lock_timeout: float = 60.0,
        durable: bool = True,
    ):
        if compression not in (None, "gzip", "lzf"):
            raise ValueError("compression must be None, 'gzip' or 'lzf'")
        if int(chunk_rows) < 1 or int(max_segments) < 1:
            raise ValueError("chunk_rows and max_segments must be >= 1")
        self.location = Path(location)
        self.analysis_name = analysis_name  # validated by the property setter
        self.compression = compression
        self.compression_opts = compression_opts if compression == "gzip" else None
        self.chunk_rows = int(chunk_rows)
        self.max_segments = int(max_segments)
        self.lock_timeout = float(lock_timeout)
        self.durable = bool(durable)
        self._durable_entries: set[tuple[int, int]] = set()  # (st_dev, st_ino) of dirs whose entry was fsynced

    @property
    def analysis_name(self) -> str:
        return self._analysis_name

    @analysis_name.setter
    def analysis_name(self, value: str) -> None:
        check_analysis_name(value)
        self._analysis_name = value

    @property
    def analysis_path(self) -> Path:
        return self.location / self._analysis_name

    def check_analysis_path(self) -> None:
        """Refuse an analysis directory that is a symlink or resolves outside location."""
        path = self.analysis_path
        _reject_symlink(path)
        if path.exists() and path.resolve().parent != self.location.resolve():
            raise HDF5StoreError(errno.EXDEV, f"analysis directory escapes {self.location}: {path}")

    # paths for one federate ---------------------------------------------------------------
    def file_path(self, federate: str) -> Path:
        return self.analysis_path / f"{encode_name(federate)}.h5"

    def lock_path(self, federate: str) -> Path:
        return self.analysis_path / f"{encode_name(federate)}.h5.lock"

    def segment_dir(self, federate: str) -> Path:
        return self.analysis_path / f"{encode_name(federate)}.h5.segments"

    def _temp_path(self, directory: Path, stem: str) -> Path:
        return directory / f"{stem}.tmp-{os.getpid()}-{uuid.uuid4().hex[:12]}"

    def lock(self, federate: str):
        """Writer lock; creates the lock file (and the analysis directory) if needed."""
        self.analysis_path.mkdir(parents=True, exist_ok=True)
        self.check_analysis_path()
        return _lock(self.lock_path(federate), self.lock_timeout)

    @contextmanager
    def read_lock(self, federate: str):
        """Lock held by a reader while it opens its snapshot.

        Writers create the lock file before they write anything, so if it does not
        exist no writer has started on this federate and the snapshot is taken
        without it (this also allows reading copies and read-only data stores).
        Yields True if the lock is held.
        """
        with ExitStack() as stack:
            try:
                stack.enter_context(_lock(self.lock_path(federate), self.lock_timeout, create=False))
                locked = True
            except FileNotFoundError:
                locked = False
            yield locked

    def consolidate_locked(self, federate: str) -> None:
        with self.lock(federate):
            _consolidate(self, federate)

    def federates_on_disk(self) -> list[str]:
        """Federate names that have a consolidated file or a segment directory."""
        path = self.analysis_path
        if not path.is_dir():
            return []
        self.check_analysis_path()
        names = set()
        for entry in path.iterdir():
            for suffix in (".h5", ".h5.segments"):
                if entry.name.endswith(suffix) and not entry.is_symlink():
                    try:
                        names.add(decode_name(entry.name[: -len(suffix)]))
                    except (ValueError, UnicodeDecodeError):
                        logger.warning(f"ignoring unrecognised entry {entry}")
        return sorted(names)

    def check_case_collision(self, federate: str) -> None:
        """Refuse a federate whose file name differs from an existing one only by case,
        so behaviour is the same on case-sensitive and case-insensitive filesystems."""
        mine = encode_name(federate)
        for other in self.federates_on_disk():
            theirs = encode_name(other)
            if theirs != mine and theirs.casefold() == mine.casefold():
                raise HDF5StoreError(
                    errno.EEXIST,
                    f"federate '{safe_name_log(federate)}' collides with '{safe_name_log(other)}' "
                    "on case-insensitive filesystems",
                )

    def live_segments(self, federate: str, through: int) -> list[_Segment]:
        seg_dir = self.segment_dir(federate)
        if not seg_dir.exists():
            return []
        _reject_symlink(seg_dir)
        segments = []
        for entry in seg_dir.iterdir():
            m = _SEGMENT.match(entry.name)
            if m and int(m.group(1)) > through:
                _reject_symlink(entry)
                segments.append(_Segment(entry, int(m.group(1)), m.group(2), int(m.group(3))))
        return sorted(segments, key=lambda s: s.seq)

    def create_kwargs(self) -> dict:
        kw: dict[str, Any] = {"chunks": (self.chunk_rows,), "maxshape": (None,)}
        if self.compression:
            kw["compression"] = self.compression
            if self.compression_opts is not None:
                kw["compression_opts"] = self.compression_opts
            kw["shuffle"] = True
        return kw

    def publish(self, tmp: Path, final: Path) -> None:
        """Make a closed, validated temporary file visible under its final name."""
        if self.durable:
            _fsync_path(tmp)
        os.replace(tmp, final)
        if self.durable:
            _fsync_dir(final.parent)

    def make_entry_durable(self, directory: Path) -> None:
        """fsync the parent of a directory once per directory inode, so a directory created here or
        by another process is itself durable before data inside it is acknowledged."""
        if not self.durable:
            return
        st = directory.stat()
        if (st.st_dev, st.st_ino) not in self._durable_entries:
            _fsync_dir(directory.parent)
            self._durable_entries.add((st.st_dev, st.st_ino))

    def sync_committed(self, federate: str, segments: list) -> None:
        """fsync every committed file and directory of a federate. Used when a retried batch is found
        already published, because the failed attempt may not have completed its fsync calls."""
        if not self.durable:
            return
        for seg in segments:
            _fsync_path(seg.path)
        seg_dir = self.segment_dir(federate)
        if seg_dir.is_dir():
            _fsync_dir(seg_dir)
        if self.file_path(federate).exists():
            _fsync_path(self.file_path(federate))
        _fsync_dir(self.analysis_path)
        _fsync_dir(self.location)

    def open_consolidated(self, federate: str) -> h5py.File | None:
        path = self.file_path(federate)
        _reject_symlink(path)
        try:
            f = h5py.File(path, "r")
        except FileNotFoundError:
            return None
        try:
            _validate(f, federate, None, "consolidated")
        except BaseException:
            f.close()
            raise
        return f


def _new_file(path: Path, helper: HDF5Helper, federate: str, kind: str) -> h5py.File:
    f = h5py.File(path, "w")
    f.attrs["schema_version"] = SCHEMA_VERSION
    f.attrs["backend"] = BACKEND_ID
    f.attrs["kind"] = kind
    f.attrs["analysis"] = helper.analysis_name
    f.attrs["federate"] = federate
    if kind == "consolidated":
        f.attrs["segments_through"] = np.int64(0)
        f.create_dataset(_WRITERS, shape=(0,), maxshape=(None,), dtype=_WRITERS_DTYPE, chunks=(64,))
    return f


def _write_rows(ds: h5py.Dataset, start: int, values: Any) -> None:
    dtype = ds.dtype
    if h5py.check_vlen_dtype(dtype) is not None and h5py.check_string_dtype(dtype) is None:
        # h5py 3.16 rejects slice assignment of equal-length vlen arrays; write_direct does not.
        arr = np.empty(len(values), dtype=object)
        for i, v in enumerate(values):
            arr[i] = v
        if len(arr):
            ds.write_direct(arr, dest_sel=np.s_[start:start + len(arr)])
    elif h5py.check_string_dtype(dtype) is not None:
        ds[start:start + len(values)] = np.array(values, dtype=object)
    else:
        ds[start:start + len(values)] = np.asarray(values, dtype=dtype)


def _append_columns(group: h5py.Group, data_type: str, columns: dict[str, Any]) -> None:
    n0 = int(group.attrs["nrows"])
    k = len(columns["sim_time"])
    for name in _columns(data_type):
        group[name].resize((n0 + k,))
        _write_rows(group[name], n0, columns[name])
    group.attrs["nrows"] = np.int64(n0 + k)


# --------------------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------------------
class HDF5TimeSeriesWriter(TimeSeriesWriter):
    """HDF5 time-series writer (one consolidated file per federate)."""

    def __init__(
        self,
        *,
        location: str | None = None,
        analysis_name: str = "default",
        helper: HDF5Helper | None = None,
        **helper_kwargs,
    ):
        """Initialize the HDF5 writer.

        For standalone use:
            writer = HDF5TimeSeriesWriter(location="/path/to/data", analysis_name="my_analysis")
        For managed use (by HDF5TimeSeriesManager):
            writer = HDF5TimeSeriesWriter(helper=HDF5Helper(...))
        """
        super().__init__()
        self.helper: HDF5Helper
        if helper:
            self.helper = helper
        elif location:
            self.helper = HDF5Helper(location, analysis_name, **helper_kwargs)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")
        self._writer_id = uuid.uuid4().hex
        self._batch_seq = 0
        self._pending: tuple[int, dict, int] | None = None  # (batch_seq, prepared plan, record count)
        self._touched: set[str] = set()
        self.rejected: list[tuple[TSRecord, str]] = []  # records flush() could never store, with reason

    def connect(self) -> bool:
        """Create the analysis directory if needed.

        Raises:
            HDF5StoreError: on platforms without POSIX file locking (Windows)

        Returns:
            bool: True if the directory exists and is usable
        """
        _require_supported_platform()
        try:
            self.helper.analysis_path.mkdir(parents=True, exist_ok=True)
            self.helper.check_analysis_path()
        except OSError as e:
            logger.error(f"HDF5 writer cannot use {self.helper.analysis_path}: {e}")
            return False
        self._is_connected = True
        logger.info(f"HDF5 time-series writer connected to: {self.helper.analysis_path}")
        return True

    def disconnect(self) -> None:
        """Consolidate committed segments into each federate's file and disconnect.

        Unflushed records are not written; call flush() first.
        """
        if self.buffer_size:
            logger.warning(f"HDF5 writer disconnecting with {self.buffer_size} unflushed records")
        if self._is_connected:
            self.consolidate_touched()
        self._is_connected = False

    def consolidate_touched(self) -> bool:
        """Consolidate every federate this writer has written to since the last call.

        Returns:
            bool: True if all consolidations succeeded (data stays committed in segments otherwise)
        """
        ok = True
        for federate in sorted(self._touched):
            try:
                self.helper.consolidate_locked(federate)
            except Exception as e:  # noqa: BLE001 - committed data stays in segments
                ok = False
                logger.error(f"consolidation of '{safe_name_log(federate)}' failed; "
                             f"its committed data remains in segments: {e}")
        self._touched.clear()
        return ok

    @property
    def buffer_size(self) -> int:
        """Number of records not yet committed (buffered plus pending retry)."""
        return len(self._buffer) + (self._pending[2] if self._pending else 0)

    def flush(self) -> bool:
        """Commit buffered records.

        Retry contract: if a flush fails on I/O, its records stay pending in this
        writer and are committed, before anything newer, by the next flush() or
        write_records() call of the same writer; a retry never duplicates records
        already committed to a federate. Records that can never be stored (invalid
        names, unsupported types, lossy values, malformed objects) are removed,
        logged and appended to ``rejected``, and the flush returns False.
        Unflushed or pending records are lost if the process ends.

        Returns:
            bool: True if every buffered record is committed
        """
        if not self._commit_pending():
            return False
        if not self._buffer:
            return True
        if not self.is_connected:
            logger.error("HDF5 writer not connected. Call connect() first.")
            return False
        count = len(self._buffer)
        plan, rejected = self._prepare(self._buffer, drop_invalid=True)  # buffer kept until prepared
        self._buffer.clear()
        for record, reason in rejected:
            self.rejected.append((record, reason))
            logger.error(f"HDF5 record rejected and not stored: {reason}")
        self._batch_seq += 1
        self._pending = (self._batch_seq, plan, count - len(rejected))
        if not self._commit_pending():
            return False
        return not rejected

    def write_records(self, records: list[TSRecord]) -> bool:
        """Write records directly as one batch.

        A pending batch from an earlier failed flush() is committed first; if that
        fails, nothing is written. The whole list is rejected, with nothing written,
        if any record is invalid. Records of a failed call are not retained:
        calling again with the same records can duplicate records the failed call
        already committed to some federates. Use add_record() and flush() for
        retry-safe writes.

        Returns:
            bool: True if all records are committed
        """
        if not self.is_connected:
            logger.error("HDF5 writer not connected. Call connect() first.")
            return False
        if not self._commit_pending():
            logger.error("HDF5 write refused: an earlier batch is still pending; retry later")
            return False
        plan, rejected = self._prepare(records, drop_invalid=False)
        if rejected:
            logger.error(f"HDF5 batch rejected, nothing written: {rejected[0][1]}")
            return False
        self._batch_seq += 1
        return self._commit(self._batch_seq, plan)

    def _commit_pending(self) -> bool:
        """Commit the pending batch, if any. Batches of a writer therefore commit in
        sequence order, which the per-writer de-duplication relies on."""
        if self._pending is None:
            return True
        if not self._commit(*self._pending[:2]):
            return False
        self._pending = None
        return True

    def _prepare(self, records: list[TSRecord], drop_invalid: bool):
        """Validate and convert records before any disk I/O.

        Returns:
            tuple: (plan {federate: {data_type: {column: values}}}, [(record, reason), ...]).
                Without drop_invalid, preparation stops at the first invalid record.
        """
        plan: dict[str, dict[str, dict[str, list]]] = {}
        rejected: list[tuple[TSRecord, str]] = []
        good_federates: set[str] = set()
        for i, r in enumerate(records):
            try:
                if not isinstance(r, TSRecord):
                    raise ValidationError(f"expected TSRecord, got {type(r).__name__}")
                if r.federate not in good_federates:
                    validate_name(r.federate, context="federate")
                    encode_name(r.federate)
                    good_federates.add(r.federate)
                data_type = canonical_data_type(r.data_type)
                sim_time = _exact_float(r.sim_time, "sim_time")
                if np.isnan(sim_time):
                    raise ValidationError("sim_time is NaN")
                value, kind = _encode_value(data_type, r.data_value)
                row = {
                    "real_time": _to_ns(r.real_time),
                    "sim_time": sim_time,
                    "scenario": _text(r.scenario, "scenario"),
                    "data_name": _text(r.data_name, "data_name"),
                    "data_value": value,
                }
                if data_type == "hdt_endpoint":
                    rf, rep = r.receiving_federate, r.receiving_endpoint
                    row["receiving_federate"] = "" if rf is None else _text(rf, "receiving_federate")
                    row["receiving_endpoint"] = "" if rep is None else _text(rep, "receiving_endpoint")
                    row["null_mask"] = (rf is None) | ((rep is None) << 1)
                    row["value_kind"] = kind
            except Exception as e:  # noqa: BLE001 - any failure to convert a record rejects that record
                where = "?"
                if isinstance(r, TSRecord):
                    where = f"{safe_name_log(str(r.federate))}, {safe_name_log(str(r.data_name))}"
                rejected.append((r, f"record {i} ({where}): {type(e).__name__}: {e}"))
                if not drop_invalid:
                    break
                continue
            columns = plan.setdefault(r.federate, {}).setdefault(data_type, {})
            for key, val in row.items():
                columns.setdefault(key, []).append(val)
        return plan, rejected

    def _commit(self, batch_seq: int, plan: dict) -> bool:
        if not self.is_connected:
            logger.error("HDF5 writer not connected. Call connect() first.")
            return False
        for federate, types in plan.items():
            try:
                with self.helper.lock(federate):
                    live = _commit_segment(self.helper, federate, types, self._writer_id, batch_seq)
                    self._touched.add(federate)
                    try:
                        if live >= self.helper.max_segments:
                            _consolidate(self.helper, federate)
                    except Exception as e:  # noqa: BLE001 - the batch itself is committed
                        logger.error(f"consolidation of '{safe_name_log(federate)}' failed; "
                                     f"committed data remains in segments: {e}")
            except Exception as e:  # noqa: BLE001
                logger.error(f"HDF5 write for federate '{safe_name_log(federate)}' failed: {e}")
                return False
        return True


def _committed_seq(helper: HDF5Helper, federate: str, writer_id: str, segments: list[_Segment],
                   consolidated: h5py.File | None) -> int:
    best = 0
    if consolidated is not None:
        table = consolidated[_WRITERS][()]
        match = table["batch_seq"][table["writer_id"] == writer_id.encode()]
        if match.size:
            best = int(match.max())
    for s in segments:
        if s.writer_id == writer_id:
            best = max(best, s.batch_seq)
    return best


def _remove_leftovers(helper: HDF5Helper, federate: str, through: int) -> None:
    """Delete temporary files of interrupted writers and already-consolidated segments.
    Caller holds the federate lock."""
    prefix = f"{encode_name(federate)}.h5.tmp-"
    for entry in helper.analysis_path.iterdir():
        if entry.name.startswith(prefix) and not entry.is_symlink():
            entry.unlink()
    seg_dir = helper.segment_dir(federate)
    if seg_dir.is_dir() and not seg_dir.is_symlink():
        stale, consolidated = [], []
        for entry in seg_dir.iterdir():
            m = _SEGMENT.match(entry.name)
            if ".tmp-" in entry.name:
                stale.append(entry)
            elif m and int(m.group(1)) <= through:
                consolidated.append(entry)
        if consolidated and helper.durable:
            # The consolidation that covered these segments may have failed before its fsync:
            # make the consolidated file durable before deleting the only other copy of the data.
            _fsync_path(helper.file_path(federate))
            _fsync_dir(helper.analysis_path)
        for entry in stale + consolidated:
            entry.unlink()


def _commit_segment(helper: HDF5Helper, federate: str, types: dict, writer_id: str,
                    batch_seq: int) -> int:
    """Write one batch for one federate as a new immutable segment. Caller holds the lock.

    Returns:
        int: number of live (unconsolidated) segments afterwards
    """
    helper.check_case_collision(federate)
    consolidated = helper.open_consolidated(federate)
    try:
        through = int(consolidated.attrs["segments_through"]) if consolidated is not None else 0
        _remove_leftovers(helper, federate, through)
        segments = helper.live_segments(federate, through)
        if batch_seq <= _committed_seq(helper, federate, writer_id, segments, consolidated):
            helper.sync_committed(federate, segments)  # the earlier attempt may have failed before its fsync
            logger.info(f"batch {batch_seq} already committed for '{safe_name_log(federate)}'; synced")
            return len(segments)
    finally:
        if consolidated is not None:
            consolidated.close()
    seq = max([through] + [s.seq for s in segments]) + 1
    seg_dir = helper.segment_dir(federate)
    if not seg_dir.exists():
        seg_dir.mkdir()
    _reject_symlink(seg_dir)
    final = seg_dir / f"{seq:016d}-{writer_id}-{batch_seq:016d}.h5"
    tmp = helper._temp_path(seg_dir, final.name)
    try:
        with _new_file(tmp, helper, federate, "segment") as f:
            f.attrs["segment_seq"] = np.int64(seq)
            for data_type, columns in types.items():
                g = f.create_group(data_type)
                k = len(columns["sim_time"])
                for name, dtype in _columns(data_type).items():
                    g.create_dataset(name, shape=(k,), dtype=dtype)
                    _write_rows(g[name], 0, columns[name])
                g.attrs["nrows"] = np.int64(k)
        with h5py.File(tmp, "r") as f:
            counts = _validate(f, federate, None, "segment")
        if counts != {dt: len(c["sim_time"]) for dt, c in types.items()}:
            raise HDF5StoreError(errno.EIO, f"segment {tmp} failed verification")
        helper.publish(tmp, final)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    helper.make_entry_durable(seg_dir)
    helper.make_entry_durable(helper.analysis_path)
    return len(segments) + 1


def _consolidate(helper: HDF5Helper, federate: str) -> None:
    """Fold all live segments into a new copy of the consolidated file and atomically
    replace it (copy-on-write). Caller holds the federate lock."""
    final = helper.file_path(federate)
    consolidated = helper.open_consolidated(federate)
    if consolidated is not None:
        through = int(consolidated.attrs["segments_through"])
        expected = {name: int(g.attrs["nrows"]) for name, g in consolidated.items() if name != _WRITERS}
        consolidated.close()
    else:
        through, expected = 0, {}
    segments = helper.live_segments(federate, through)
    if not segments:
        return
    tmp = helper._temp_path(helper.analysis_path, final.name)
    try:
        if final.exists():
            shutil.copyfile(final, tmp)
            out = h5py.File(tmp, "a")
        else:
            out = _new_file(tmp, helper, federate, "consolidated")
        with out:
            writers = {row["writer_id"].decode(): int(row["batch_seq"]) for row in out[_WRITERS][()]}
            pending: dict[str, dict[str, list]] = {}
            for seg in segments:  # read and validate every segment first, in commit order
                with h5py.File(seg.path, "r") as src:
                    _validate(src, federate, None, "segment")
                    for data_type, g in src.items():
                        columns = pending.setdefault(data_type, {})
                        for c in g:
                            columns.setdefault(c, []).append(g[c][()])
                        expected[data_type] = expected.get(data_type, 0) + int(g.attrs["nrows"])
                writers[seg.writer_id] = max(writers.get(seg.writer_id, 0), seg.batch_seq)
            for data_type, columns in pending.items():  # one append per data type
                if data_type not in out:
                    dst = out.create_group(data_type)
                    dst.attrs["nrows"] = np.int64(0)
                    for name, dtype in _columns(data_type).items():
                        dst.create_dataset(name, shape=(0,), dtype=dtype, **helper.create_kwargs())
                    dst["real_time"].attrs["units"] = "ns since 1970-01-01T00:00:00Z"
                _append_columns(out[data_type], data_type, {c: np.concatenate(v) for c, v in columns.items()})
            table = np.array(sorted(writers.items()), dtype=_WRITERS_DTYPE)
            out[_WRITERS].resize((len(table),))
            if len(table):
                out[_WRITERS][:] = table
            out.attrs["segments_through"] = np.int64(segments[-1].seq)
        with h5py.File(tmp, "r") as f:
            if _validate(f, federate, None, "consolidated") != expected:
                raise HDF5StoreError(errno.EIO, f"consolidated file {tmp} failed verification")
        helper.publish(tmp, final)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    for seg in segments:
        seg.path.unlink(missing_ok=True)
    seg_dir = helper.segment_dir(federate)
    try:
        seg_dir.rmdir()  # only succeeds when empty; writers create segments under the same lock
    except OSError:
        if helper.durable:
            _fsync_dir(seg_dir)
    else:
        if helper.durable:
            _fsync_dir(helper.analysis_path)


# --------------------------------------------------------------------------------------
# Reader
# --------------------------------------------------------------------------------------
def _as_list(value: str | list | None) -> list | None:
    if value is None:
        return None
    return [value] if isinstance(value, str) else list(value)


class HDF5TimeSeriesReader(TimeSeriesReader):
    """HDF5 time-series reader; each federate is read from one committed snapshot."""

    def __init__(
        self,
        *,
        location: str | None = None,
        analysis_name: str = "default",
        helper: HDF5Helper | None = None,
        **helper_kwargs,
    ):
        """Initialize the HDF5 reader.

        For standalone use:
            reader = HDF5TimeSeriesReader(location="/path/to/data", analysis_name="my_analysis")
        For managed use (by HDF5TimeSeriesManager):
            reader = HDF5TimeSeriesReader(helper=HDF5Helper(...))
        """
        super().__init__()
        self.helper: HDF5Helper
        if helper:
            self.helper = helper
        elif location:
            self.helper = HDF5Helper(location, analysis_name, **helper_kwargs)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")

    def connect(self) -> bool:
        """Check the analysis directory.

        Raises:
            HDF5StoreError: on platforms without POSIX file locking (Windows)

        Returns:
            bool: True (a missing directory simply holds no data yet)
        """
        _require_supported_platform()
        if not self.helper.analysis_path.exists():
            logger.warning(f"Analysis path does not exist: {self.helper.analysis_path}")
        self._is_connected = True
        logger.info(f"HDF5 time-series reader connected to: {self.helper.analysis_path}")
        return True

    def disconnect(self) -> None:
        """Close connection (no-op for files)."""
        self._is_connected = False

    def _snapshot(self, federate: str, visit) -> None:
        """Call visit(data_type, group) for the consolidated file and every live segment
        of one committed state of the federate.

        The files are opened while holding the federate lock, so no consolidation or
        deletion can run between opening the consolidated file and enumerating the
        segments; the data is read after the lock is released, from the open
        (immutable) files.
        """
        handles: list[h5py.File] = []
        try:
            while True:
                with self.helper.read_lock(federate) as locked:
                    consolidated = self.helper.open_consolidated(federate)
                    through = 0
                    if consolidated is not None:
                        handles.append(consolidated)
                        through = int(consolidated.attrs["segments_through"])
                    for seg in self.helper.live_segments(federate, through):
                        f = h5py.File(seg.path, "r")
                        handles.append(f)
                        _validate(f, federate, None, "segment")
                # Without a lock file no writer had started; if one has appeared meanwhile, retake with the lock.
                if locked or not self.helper.lock_path(federate).exists():
                    break
                for f in handles:
                    f.close()
                handles.clear()
            for f in handles:
                for name, obj in f.items():
                    if name != _WRITERS:
                        visit(name, obj)
        finally:
            for f in handles:
                f.close()

    def read_data(
        self,
        start_time: float | None = None,
        duration: float | None = None,
        scenario_name: str | list | None = None,
        federate_name: str | list | None = None,
        data_name: str | list | None = None,
        data_type: str | list | None = None,
    ) -> pd.DataFrame:
        """Read time-series data from HDF5 files.

        Args:
            start_time (Optional[float], optional): Start time (ordinal time
                in seconds) for requested data. Defaults to None.
            duration (Optional[float], optional): Length of time (in seconds)
                from the data to read. Defaults to None.
            scenario_name (Optional[str | list], optional): Name(s) of scenario to read.
            federate_name (Optional[str | list], optional): Name(s) of federate to read.
            data_name (Optional[str | list], optional): Name(s) of data to read.
            data_type (Optional[str | list], optional): Data type(s) to read; aliases accepted.

        Raises:
            HDF5StoreError: if stored data is missing, unreadable or fails validation.
                Partial results are never returned silently.

        Returns:
            pd.DataFrame: requested data sorted by sim_time
        """
        if not self.is_connected:
            logger.error("HDF5 reader not connected. Call connect() first.")
            return pd.DataFrame()
        scenarios, names = _as_list(scenario_name), _as_list(data_name)
        types = None
        if data_type is not None:
            types = set()
            for t in _as_list(data_type):
                try:
                    types.add(canonical_data_type(t))
                except UnsupportedDataTypeError:
                    pass
        on_disk = self.helper.federates_on_disk()
        federates = on_disk if federate_name is None else [f for f in _as_list(federate_name) if f in on_disk]
        parts = []
        for federate in federates:
            def visit(dt, group, federate=federate):
                if types is None or dt in types:
                    part = _read_group(group, dt, federate, start_time, duration, scenarios, names)
                    if part is not None:
                        parts.append(part)
            try:
                self._snapshot(federate, visit)
            except HDF5StoreError:
                raise
            except (OSError, KeyError, ValueError) as e:
                raise HDF5StoreError(errno.EIO, f"cannot read data of '{federate}': {e}") from e
        return _assemble(parts)

    def list_federates(self) -> list[str]:
        """List federates with data in the analysis.

        Returns:
            list[str]: federate names
        """
        if not self.is_connected:
            return []
        return self.helper.federates_on_disk()

    def list_data_types(self, federate_names: list[str] | None = None) -> list[str]:
        """List data types stored for the given federates (all federates by default).

        Returns:
            list[str]: data types, one entry per federate and type, sorted
        """
        if not self.is_connected:
            return []
        out = []
        for federate in federate_names if federate_names is not None else self.list_federates():
            if federate not in self.helper.federates_on_disk():
                continue
            found: set[str] = set()

            def visit(dt, group, found=found):
                if int(group.attrs["nrows"]):
                    found.add(dt)

            self._snapshot(federate, visit)
            out.extend(found)
        return sorted(out)

    def list_scenarios(self) -> list[str]:
        """List the unique scenarios in the analysis.

        Returns:
            list[str]: scenario names
        """
        if not self.is_connected:
            return []
        scenarios: set[str] = set()
        for federate in self.list_federates():
            self._snapshot(federate, lambda dt, g: scenarios.update(g["scenario"].asstr()[()].tolist()))
        return sorted(scenarios)

    def get_time_range(self, **kwargs) -> dict[str, float]:
        """Get the minimum and maximum simulation times of the selected data.

        Returns:
            dict[str, float]: {"min_time": float, "max_time": float}
        """
        df = self.read_data(**kwargs)
        if df.empty:
            return {"min_time": 0.0, "max_time": 0.0}
        return {"min_time": float(df["sim_time"].min()), "max_time": float(df["sim_time"].max())}


def _read_group(group, data_type, federate, start_time, duration, scenarios, names) -> dict | None:
    """Selected rows of one data-type group as {column: 1-D numpy array}."""
    n = int(group.attrs["nrows"])
    if n == 0:
        return None
    sim = group["sim_time"][()]
    mask = np.ones(n, dtype=bool)
    if start_time is not None:
        mask &= sim >= start_time
    if duration is not None:
        mask &= sim < (start_time or 0) + duration
    if scenarios is not None:
        mask &= np.isin(group["scenario"].asstr()[()], scenarios)
    if names is not None:
        mask &= np.isin(group["data_name"].asstr()[()], names)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return None

    def column(name, text=False):
        values = (group[name].asstr() if text else group[name])[()]
        values = values if idx.size == n else values[idx]
        return values.astype(object) if text else values

    def objects(values):
        out = np.empty(len(values), dtype=object)
        out[:] = values if isinstance(values, list) else list(values)
        return out

    part = {
        "real_time": column("real_time"),
        "sim_time": column("sim_time"),
        "scenario": column("scenario", True),
        "federate": np.full(idx.size, federate, dtype=object),
        "data_name": column("data_name", True),
    }
    raw = column("data_value")
    if data_type == "hdt_endpoint":
        mask_bits, kinds = column("null_mask"), column("value_kind")
        for name, bit in (("receiving_federate", 1), ("receiving_endpoint", 2)):
            values = column(name, True)
            values[(mask_bits & bit) == bit] = None
            part[name] = values
        part["data_value"] = objects([_decode_value(data_type, raw[i], int(kinds[i])) for i in range(idx.size)])
    else:
        part["data_value"] = objects([_decode_value(data_type, x) for x in raw])
    return part


def _assemble(parts: list[dict]) -> pd.DataFrame:
    """Build the result DataFrame directly from column arrays, sorted by sim_time.

    pandas.concat is not used: pandas 2.x replaces an object column whose values are all
    NA-like (pd.isna(complex(nan, 1)) is True) with a NaN fill value when concatenating frames.
    """
    if not parts:
        return pd.DataFrame()
    endpoint = any("receiving_federate" in p for p in parts)
    columns = ["real_time", "sim_time", "scenario", "federate", "data_name"]
    columns += ["receiving_federate", "receiving_endpoint"] if endpoint else []
    columns.append("data_value")
    merged = {}
    for name in columns:
        pieces = []
        for p in parts:
            if name in p:
                pieces.append(p[name])
            else:  # receiving_* of non-endpoint rows: NaN, as pandas.concat produced
                fill = np.empty(len(p["sim_time"]), dtype=object)
                fill[:] = np.nan
                pieces.append(fill)
        merged[name] = np.concatenate(pieces)
    order = np.argsort(merged["sim_time"], kind="stable")
    data = {}
    for name in columns:
        values = merged[name][order]
        if name == "real_time":
            data[name] = pd.to_datetime(values, unit="ns", utc=True)
        elif name in ("data_value", "receiving_federate", "receiving_endpoint"):
            data[name] = pd.Series(values, dtype=object)  # keep Python objects (None, complex, bytes)
        else:
            data[name] = values  # pandas infers the dtype, as for the other backends
    return pd.DataFrame(data)


# --------------------------------------------------------------------------------------
# Manager
# --------------------------------------------------------------------------------------
class HDF5TimeSeriesManager(TimeSeriesManager):
    """
    Joint HDF5 time-series manager using composition.
    Manages a shared Helper for a single reader and writer instance.
    """

    _HELPER_OPTIONS = ("compression", "compression_opts", "chunk_rows", "max_segments",
                       "lock_timeout", "durable")

    def __init__(self, *, location: str, analysis_name: str = "default", **kwargs):
        """Initialize HDF5 time-series manager.

        Args:
            location (str): directory holding analysis directories
            analysis_name (str): analysis name (a single directory name)
            **kwargs: compression ("gzip", "lzf" or None), compression_opts,
                chunk_rows, max_segments, lock_timeout (seconds) and durable (fsync)
        """
        options = {k: kwargs.pop(k) for k in list(kwargs) if k in self._HELPER_OPTIONS}
        super().__init__(**kwargs)
        self.helper: HDF5Helper = HDF5Helper(location, analysis_name, **options)
        self.writer: HDF5TimeSeriesWriter = HDF5TimeSeriesWriter(helper=self.helper)
        self.reader: HDF5TimeSeriesReader = HDF5TimeSeriesReader(helper=self.helper)

    def connect(self) -> bool:
        """Establish connection for both reader and writer."""
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Consolidate committed data and close connection for both reader and writer."""
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def list_federates(self) -> list[str]:
        """Lists federates with data in data backend"""
        return self.reader.list_federates()

    def list_data_types(self, federate_names: list[str] | None = None) -> list[str]:
        """Lists data types for the given federates in the data backend"""
        return self.reader.list_data_types(federate_names)

    def list_scenarios(self) -> list[str]:
        """List of scenarios in the data backend"""
        return self.reader.list_scenarios()

    def get_time_range(self, **kwargs) -> dict[str, float]:
        """Get time range of data in data backend"""
        return self.reader.get_time_range(**kwargs)

    def consolidate(self) -> bool:
        """Fold committed segments of every federate into its consolidated file.

        Returns:
            bool: True if every federate was consolidated
        """
        ok = True
        for federate in self.helper.federates_on_disk():
            try:
                self.helper.consolidate_locked(federate)
            except Exception as e:  # noqa: BLE001
                logger.error(f"consolidation of '{safe_name_log(federate)}' failed: {e}")
                ok = False
        return ok

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """NOT IMPLEMENTED

        Raises:
            NotImplementedError:
        """
        raise NotImplementedError(
            "Scenario deletion is not supported for HDF5 files. "
            "Consider using a database backend for selective deletion."
        )

    def delete_federate_data(self, federate_name: str) -> bool:
        """Delete all data for a specific federate, waiting for any active writer.

        Args:
            federate_name (str): federate for which to delete data

        Returns:
            bool: True if data was deleted, False if none existed or deletion failed
        """
        try:
            validate_name(federate_name, context="federate")
            if federate_name not in self.helper.federates_on_disk():
                logger.warning(f"No HDF5 data for federate: {safe_name_log(federate_name)}")
                return False
            with self.helper.lock(federate_name):
                path = self.helper.file_path(federate_name)
                seg_dir = self.helper.segment_dir(federate_name)
                _reject_symlink(path)
                _reject_symlink(seg_dir)
                path.unlink(missing_ok=True)
                if seg_dir.exists():
                    shutil.rmtree(seg_dir)
                _remove_leftovers(self.helper, federate_name, 0)
                if self.helper.durable:
                    _fsync_dir(self.helper.analysis_path)
            logger.debug(f"Deleted all data for federate: {safe_name_log(federate_name)}")
            return True
        except (ValidationError, OSError) as e:
            logger.error(f"Failed to delete federate data for '{safe_name_log(federate_name)}': {e}")
            return False

    def backup_analysis(self, backup_path: str) -> bool:
        """Back up the analysis as one consolidated, verified file per federate.

        The destination must not exist, be an empty directory, or be an earlier HDF5
        backup of this same analysis (only ``<federate>.h5`` files of this analysis).
        Anything else is refused, so no unrelated file is overwritten or deleted. The
        complete backup is built in a temporary sibling directory and then replaces the
        destination, so it holds exactly the federates present now: a federate deleted
        since an earlier backup to the same destination is no longer in it, and an
        earlier backup of an analysis whose federates were all deleted becomes empty.
        If the analysis has no data and the destination does not exist, nothing is
        created. Each federate is consolidated and copied while holding its lock, so
        every file is a committed state; different federates may reflect different
        points in time.

        On failure (False) the destination is put back as it was before the call. If
        even that cannot be completed and made durable, nothing is deleted: the earlier
        backup and the new copy stay in hidden ``.<name>.*`` siblings of the destination,
        and the log names them.

        Args:
            backup_path (str): destination directory

        Returns:
            bool: True if every federate was backed up and verified, and with
            ``durable`` the replaced destination was synced to disk
        """
        dest = Path(backup_path)
        problem = self._backup_destination_problem(dest)
        if problem:
            logger.error(f"Refusing to back up analysis '{self.analysis_name}' to {dest}: {problem}")
            return False
        federates = self.helper.federates_on_disk()
        if not federates and not dest.exists():
            logger.warning(f"Analysis '{self.analysis_name}' does not exist, nothing to backup")
            return True
        dest.parent.mkdir(parents=True, exist_ok=True)
        staging = self.helper._temp_path(dest.parent, f".{dest.name}")
        previous = None
        published = False
        try:
            staging.mkdir()
            for federate in federates:
                with self.helper.lock(federate):
                    _consolidate(self.helper, federate)
                    src = self.helper.file_path(federate)
                    _reject_symlink(src)
                    shutil.copyfile(src, staging / src.name)
                with h5py.File(staging / src.name, "r") as f:
                    _validate(f, federate, None, "consolidated")
                if self.helper.durable:
                    _fsync_path(staging / src.name)
            if self.helper.durable:
                _fsync_dir(staging)
            if dest.exists():
                previous = self.helper._temp_path(dest.parent, f".{dest.name}.previous")
                os.rename(dest, previous)
            os.rename(staging, dest)
            published = True
            if self.helper.durable:
                _fsync_dir(dest.parent)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to backup analysis '{self.analysis_name}': {e}")
            self._undo_backup(dest, staging, previous, published)
            return False
        if previous is not None:
            shutil.rmtree(previous, ignore_errors=True)
        logger.info(f"Backed up analysis '{self.analysis_name}' to {dest}")
        return True

    def _undo_backup(self, dest: Path, staging: Path, previous: Path | None, published: bool) -> None:
        """Put dest back as it was before a failed backup; delete the new copy only once that is durable."""
        try:
            if published:
                os.rename(dest, staging)  # move the new backup aside
            if previous is not None:
                os.rename(previous, dest)  # put the earlier backup back
            if self.helper.durable and (published or previous is not None):
                _fsync_dir(dest.parent)
        except OSError as e:
            kept = [str(p) for p in (previous, staging) if p is not None and p.exists()]
            logger.error(f"Could not restore backup destination {dest}: {e}; "
                         f"nothing was deleted, kept: {', '.join(kept) or 'none'}")
            return
        shutil.rmtree(staging, ignore_errors=True)

    def _backup_destination_problem(self, dest: Path) -> str | None:
        """Why dest cannot receive a backup of this analysis, or None if it can."""
        if dest.is_symlink():
            return "destination is a symbolic link"
        here, there = self.helper.analysis_path.resolve(), dest.resolve()
        if there == here or here in there.parents or there in here.parents:
            return "destination overlaps the analysis directory"
        if not dest.exists():
            return None
        if not dest.is_dir():
            return "destination exists and is not a directory"
        for entry in dest.iterdir():
            if entry.is_symlink() or not entry.is_file() or not entry.name.endswith(".h5"):
                return f"it contains '{entry.name}', which is not part of an HDF5 backup of this analysis"
            try:
                federate = decode_name(entry.name[:-3])
                with h5py.File(entry, "r") as f:
                    _validate(f, federate, self.analysis_name, "consolidated")  # same analysis only
            except Exception:  # noqa: BLE001
                return f"it contains '{entry.name}', which is not part of an HDF5 backup of this analysis"
        return None

    @property
    def location(self) -> Path:
        """Location property"""
        return self.helper.location

    @property
    def analysis_name(self) -> str:
        """Get the current analysis name."""
        return self.helper.analysis_name

    @analysis_name.setter
    def analysis_name(self, value: str) -> None:
        """Set the analysis name and update the shared helper.

        Raises:
            ValueError: if records are buffered or pending; they would otherwise
                be written into the new analysis. Flush first.
        """
        if self.writer.buffer_size:
            raise ValueError(
                f"cannot change analysis while {self.writer.buffer_size} records are not committed; "
                "call flush() first"
            )
        check_analysis_name(value)
        self.writer.consolidate_touched()  # finish the old analysis
        self.helper.analysis_name = value
