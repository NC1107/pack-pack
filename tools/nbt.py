"""Minimal reader for Minecraft's NBT format (gzipped .dat files), standard library only."""

from __future__ import annotations

import gzip
import io
import struct
from pathlib import Path
from typing import Any, Protocol

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = range(7)
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = range(7, 13)

_SCALARS = {
    TAG_BYTE: ">b", TAG_SHORT: ">h", TAG_INT: ">i", TAG_LONG: ">q", TAG_FLOAT: ">f", TAG_DOUBLE: ">d",
}
_ARRAYS = {TAG_BYTE_ARRAY: ">b", TAG_INT_ARRAY: ">i", TAG_LONG_ARRAY: ">q"}


class Readable(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


def _unpack(stream: Readable, fmt: str) -> Any:
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, stream.read(size))[0]


def _string(stream: Readable) -> str:
    length = _unpack(stream, ">H")
    return stream.read(length).decode("utf-8", errors="replace")


def _payload(stream: Readable, tag: int) -> Any:
    if tag in _SCALARS:
        return _unpack(stream, _SCALARS[tag])
    if tag in _ARRAYS:
        count = _unpack(stream, ">i")
        return [_unpack(stream, _ARRAYS[tag]) for _ in range(count)]
    if tag == TAG_STRING:
        return _string(stream)
    if tag == TAG_LIST:
        item_tag = _unpack(stream, ">b")
        count = _unpack(stream, ">i")
        return [_payload(stream, item_tag) for _ in range(count)]
    if tag == TAG_COMPOUND:
        compound = {}
        while (child := _unpack(stream, ">b")) != TAG_END:
            name = _string(stream)
            compound[name] = _payload(stream, child)
        return compound
    raise ValueError(f"unknown NBT tag {tag}")


def _root(stream: Readable) -> dict:
    if _unpack(stream, ">b") != TAG_COMPOUND:
        raise ValueError("NBT data does not start with a compound tag")
    _string(stream)
    return _payload(stream, TAG_COMPOUND)


def read(path: Path) -> dict:
    """Read a gzipped NBT file and return its root compound as nested dicts and lists."""
    with gzip.open(path, "rb") as stream:
        return _root(stream)


def read_bytes(data: bytes) -> dict:
    """Read uncompressed NBT, e.g. a chunk after zlib-decompressing it from a region file."""
    return _root(io.BytesIO(data))
