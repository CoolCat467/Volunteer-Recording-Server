"""Serializable - Serializable records."""

# Programmed by CoolCat467

from __future__ import annotations

# Serializable - Serializable records
# Copyright (C) 2026  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "Serializable"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


from abc import abstractmethod
from collections.abc import (
    Generator,
    Iterable,
    Iterator,
    MutableMapping,
    MutableSequence,
    Sequence,
)
from typing import TYPE_CHECKING, Any, NamedTuple, Self, cast, overload

import orjson
import trio

if TYPE_CHECKING:
    from os import PathLike


class Serializable[T](trio.abc.AsyncResource):
    """Serializable data able to be saved and loaded from a file."""

    __slots__ = ("data", "path")

    def __init__(self, path: PathLike[str] | str) -> None:
        """Initialize this instance."""
        self.path = trio.Path(path)
        self.data: T

    def __repr__(self) -> str:
        """Return representation of this class."""
        return f"{self.__class__.__name__}({self.path!r})"

    def deserialize(self, data: bytes) -> Any:
        """Return value from deserializing data."""
        return orjson.loads(data)

    async def load(self) -> None:
        """Load data from path."""
        async with await self.path.open("rb") as fp:
            self.data = self.deserialize(await fp.read())

    def serialize(self) -> bytes:
        """Return serialized data to write to file."""
        return orjson.dumps(
            self.data,
            option=orjson.OPT_APPEND_NEWLINE
            | orjson.OPT_UTC_Z
            | orjson.OPT_NAIVE_UTC,
        )

    async def write_file(self) -> None:
        """Write current data to path."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        serialized = self.serialize()
        async with await self.path.open("wb") as fp:
            await fp.write(serialized)

    async def __aenter__(self) -> Self:
        """Return self after loading data from path."""
        self.path = await self.path.absolute()
        await self.load()
        return self

    @property
    def loaded(self) -> bool:
        """Return if loaded or not."""
        return hasattr(self, "data")

    async def aclose(self) -> None:  # noqa: D102
        if not self.loaded:
            return

        await self.write_file()
        del self.data


class SerializableDict[KT, VT](
    Serializable[MutableMapping[KT, VT]],
    MutableMapping[KT, VT],
):
    """Serializable dictionary."""

    __slots__ = ()

    def __getitem__(self, key: KT) -> VT:
        """Return self[key]."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return self.data[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        """Set self[key] to value."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        self.data[key] = value

    def __delitem__(self, key: KT) -> None:
        """Delete self[key]."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        del self.data[key]

    def __iter__(self) -> Iterator[KT]:
        """Implement iter(self)."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return iter(self.data)

    def __len__(self) -> int:
        """Return len(self)."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return len(self.data)


class SerializableSequence[T](Serializable[MutableSequence[T]], Sequence[T]):
    """Serializable Sequence."""

    __slots__ = ()

    @overload
    def __getitem__(self, index: int, /) -> T: ...
    @overload
    def __getitem__(
        self,
        index: slice[int | None, int | None, int | None],
        /,
    ) -> MutableSequence[T]: ...

    def __getitem__(
        self,
        index: int | slice[int | None, int | None, int | None],
    ) -> T | MutableSequence[T]:
        """Return self[key]."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return self.data[index]

    def __iter__(self) -> Iterator[T]:
        """Implement iter(self)."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return iter(self.data)

    def __len__(self) -> int:
        """Implement len(self)."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        return len(self.data)


class SerializableMutableSequence[T](
    SerializableSequence[T],
    MutableSequence[T],
):
    """Serializable MutableSequence."""

    __slots__ = ()

    @overload
    def __setitem__(self, index: int, value: T, /) -> None: ...
    @overload
    def __setitem__(
        self,
        index: slice[int | None, int | None, int | None],
        value: Iterable[T],
        /,
    ) -> None: ...

    def __setitem__(
        self,
        index: int | slice[int | None, int | None, int | None],
        value: T | Iterable[T],
    ) -> None:
        """Set self[key] to value."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        if isinstance(index, slice):
            assert isinstance(value, Iterable)
            self.data[index] = value
            return
        self.data[index] = cast("T", value)

    @overload
    def __delitem__(self, index: int, /) -> None: ...
    @overload
    def __delitem__(
        self,
        index: slice[int | None, int | None, int | None],
        /,
    ) -> None: ...

    def __delitem__(
        self,
        index: int | slice[int | None, int | None, int | None],
    ) -> None:
        """Delete self[key]."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        del self.data[index]

    def insert(self, before: int, object_: T, /) -> None:
        """Insert object before index."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        self.data.insert(before, object_)


class Record[T](NamedTuple):
    """Database entry."""

    id_: int
    entry: T


class Database[T](SerializableSequence[T]):
    """Database of append or overwrite existing only data."""

    __slots__ = ()

    @abstractmethod
    def deserialize_entry(self, entry: Any) -> T:
        """Return deserialized version of entry."""

    def deserialize(self, data: bytes) -> MutableSequence[T]:  # noqa: D102
        return list(map(self.deserialize_entry, super().deserialize(data)))

    async def load(self) -> None:  # noqa: D102
        if not await self.path.exists():
            self.data = []
            return
        await super().load()

    async def write_file(self) -> None:  # noqa: D102
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        folder = self.path.parent
        if not await folder.exists():
            await folder.mkdir(parents=True)
        await super().write_file()

    @overload
    def __setitem__(self, index: int, value: T, /) -> None: ...
    @overload
    def __setitem__(
        self,
        index: slice[int | None, int | None, int | None],
        value: Iterable[T],
        /,
    ) -> None: ...

    def __setitem__(
        self,
        index: int | slice[int | None, int | None, int | None],
        value: T | Iterable[T],
    ) -> None:
        """Set self[index] to value."""
        if not self.loaded:
            raise RuntimeError("Not currently loaded")
        if isinstance(index, slice):
            assert isinstance(value, Iterable)
            self.data[index] = value
            return
        self.data[index] = cast("T", value)

    def add(self, value: T) -> int:
        """Return index of newly added element."""
        index = len(self)
        self.data.append(value)
        return index

    def get(self, index: int, default: T | None = None) -> T | None:
        """Return element at index or default if out of bounds."""
        if index < 0 or index > len(self):
            return default
        return self[index]

    def yield_all_entries(self) -> Generator[Record[T]]:
        """Yield all entry records."""
        for entry_id, entry in enumerate(self):
            yield Record(entry_id, entry)

    def yield_entries_by_attributes(
        self,
        **kwargs: object,
    ) -> Generator[Record[T]]:
        """Yield each entry record where the attribute exists and matches given value."""
        for entry_id, entry in enumerate(self):
            for key, value in kwargs.items():
                if not hasattr(entry, key):
                    break
                if getattr(entry, key) != value:
                    break
            else:
                # went through without hitting "break"
                yield Record(entry_id, entry)
