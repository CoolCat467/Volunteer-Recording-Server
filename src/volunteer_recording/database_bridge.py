"""Database Bridge - Self-contained module for database interfacing."""

# Programmed by CoolCat467

from __future__ import annotations

# Database Bridge - Self-contained module for database interfacing
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

__title__ = "Database Bridge"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


import datetime as dt
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any, NotRequired, Self, TypedDict

import orjson
import trio

from volunteer_recording.serializable import (
    Database,
    MappingDatabase,
    Record as Record,
)

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
    )


class SerializedUserRecord(TypedDict):
    """Serialized User record."""

    firstname: str
    lastname: str
    date_of_birth: str
    code: int
    retired: NotRequired[bool]
    is_admin: NotRequired[bool]


@dataclass(slots=True, frozen=True)
class User:
    """User record."""

    firstname: str
    lastname: str
    date_of_birth: dt.date
    code: int
    retired: bool = False
    is_admin: bool = False

    @classmethod
    def deserialize(cls, dict_: SerializedUserRecord) -> Self:
        """Return new class instance from deserializing dictionary."""
        return cls(
            firstname=dict_["firstname"],
            lastname=dict_["lastname"],
            date_of_birth=dt.date.fromisoformat(dict_["date_of_birth"]),
            code=dict_["code"],
            retired=dict_["retired"],
            is_admin=dict_["is_admin"],
        )


class UserDatabase(Database[User]):
    """Database of user records."""

    __slots__ = ()

    def deserialize_entry(self, entry: Any) -> User:  # noqa: D102
        return User.deserialize(entry)

    def yield_records_from_code(
        self,
        code: int,
    ) -> Generator[Record[User]]:
        """Yield non-retired user records with given code."""
        return self.yield_entries_by_attributes(code=code, retired=False)

    def yield_admin_records_from_code(
        self,
        code: int,
    ) -> Generator[Record[User]]:
        """Yield non-retired administrator user records with given code."""
        return self.yield_entries_by_attributes(
            code=code,
            is_admin=True,
            retired=False,
        )


class TimestampType(IntEnum):
    """Timestamp Types."""

    CHECK_IN = 0
    CHECK_OUT = auto()
    AUTO_CHECKOUT = auto()


class SerializedTimestampRecord(TypedDict):
    """Serialized Timestamp record."""

    type_: int
    time: str


@dataclass(slots=True, frozen=True)
class Timestamp:
    """Timestamp record."""

    type_: TimestampType
    time: dt.time

    @classmethod
    def deserialize(cls, dict_: SerializedTimestampRecord) -> Self:
        """Return new class instance from deserializing dictionary."""
        return cls(
            type_=TimestampType(dict_["type_"]),
            time=dt.time.fromisoformat(dict_["time"]),
        )


class SerializedCalendarRecord(TypedDict):
    """Serialized Calendar record."""

    days: dict[str, list[SerializedTimestampRecord]]


@dataclass(slots=True, frozen=True)
class Calendar:
    """Calendar record."""

    days: dict[dt.date, list[Timestamp]] = field(default_factory=dict)

    @classmethod
    def deserialize(cls, dict_: SerializedCalendarRecord) -> Self:
        """Return new class instance from deserializing dictionary."""
        return cls(
            days={
                dt.date.fromisoformat(k): list(map(Timestamp.deserialize, v))
                for k, v in dict_["days"].items()
            },
        )

    def add_timestamp(
        self,
        type_: TimestampType,
        datetime: dt.datetime,
    ) -> None:
        """Add timestamp of given time from given datetime."""
        date = datetime.date()
        day = self.days.get(date, [])
        day.append(Timestamp(type_, datetime.time()))


class TimestampDatabase(MappingDatabase[int, Calendar]):
    """Mapping Database of user ids to calendar records."""

    __slots__ = ()

    def deserialize_key(self, key: str) -> int:  # noqa: D102
        return int(key)

    def deserialize_entry(self, entry: SerializedCalendarRecord) -> Calendar:  # noqa: D102
        return Calendar.deserialize(entry)

    def serialize(self) -> bytes:
        """Return serialized data to write to file."""
        return orjson.dumps(
            self.data,
            option=orjson.OPT_APPEND_NEWLINE
            | orjson.OPT_UTC_Z
            | orjson.OPT_NAIVE_UTC
            | orjson.OPT_OMIT_MICROSECONDS
            | orjson.OPT_NON_STR_KEYS,
        )


async def run() -> None:
    """Run program."""
    ##async with UserDatabase("test.json") as database:
    ##    database.data.clear()
    ##    user = User(
    ##        "Firstname",
    ##        "Lastname",
    ##        dt.date(2000, 1, 1),
    ##        1234,
    ##    )
    ##    print(f"{user = }")
    ##    print(f"{database.data = }")
    ##
    ##    database.add(user)
    ##    print(f"{database.data = }")
    async with TimestampDatabase("timestamps.json") as database:
        database[0] = Calendar()
        calendar = database[0]
        calendar.add_timestamp(TimestampType.CHECK_IN, dt.datetime.now())
        print(f"{database.data = }")


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    trio.run(run)
