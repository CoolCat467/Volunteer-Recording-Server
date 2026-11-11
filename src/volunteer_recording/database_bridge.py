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
from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any, NamedTuple, NotRequired, Self, TypedDict

import orjson
import trio

from volunteer_recording.serializable import (
    Database,
    Record as Record,
)

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Iterable,
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


class StampType(IntEnum):
    """Timestamp Types."""

    CHECK_IN = 0
    CHECKOUT = auto()
    AUTO_CHECK_IN = auto()
    AUTO_CHECKOUT = auto()


class SerializedTimestampRecord(TypedDict):
    """Serialized Timestamp record."""

    type_: int
    time: str


@dataclass(slots=True, frozen=True)
class Timestamp:
    """Timestamp record."""

    type_: StampType
    time: dt.time

    @classmethod
    def deserialize(cls, dict_: SerializedTimestampRecord) -> Self:
        """Return new class instance from deserializing dictionary."""
        return cls(
            type_=StampType(dict_["type_"]),
            time=dt.time.fromisoformat(dict_["time"]),
        )


class SerializedCalendarRecord(TypedDict):
    """Serialized Calendar record."""

    days: dict[str, list[SerializedTimestampRecord]]


class EventCounts(NamedTuple):
    """Event count data."""

    in_: int
    out: int
    auto_in: int
    auto_out: int

    @property
    def total_in(self) -> int:
        """Return combined check-in count."""
        return self.in_ + self.auto_in

    @property
    def total_out(self) -> int:
        """Return combined checkout count."""
        return self.out + self.auto_out

    @property
    def difference(self) -> int:
        """Positive if there are more outs than ins."""
        return self.total_out - self.total_in

    def is_balanced(self) -> bool:
        """Return if number of check-ins and total checkouts are balanced."""
        return self.total_in == self.total_out

    def needs_check_in(self) -> bool:
        """Return if needs a checkout."""
        return self.difference > 0

    def needs_checkout(self) -> bool:
        """Return if needs a checkout."""
        return self.difference < 0

    @classmethod
    def from_timestamps(cls, timestamps: Iterable[StampType]) -> Self:
        """Return new class instance from timestamps."""
        event_counts = Counter(timestamps)
        assert len(StampType) == 4
        return cls(
            in_=event_counts[StampType.CHECK_IN],
            out=event_counts[StampType.CHECKOUT],
            auto_in=event_counts[StampType.AUTO_CHECK_IN],
            auto_out=event_counts[StampType.AUTO_CHECKOUT],
        )


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

    def yield_timestamp_types(self, date: dt.date) -> Generator[StampType]:
        """Yield TimestampTypes for the given date."""
        for timestamp in self.days.get(date, ()):
            yield timestamp.type_

    def get_event_counts(self, date: dt.date) -> EventCounts:
        """Return EventCounts object for the given day."""
        return EventCounts.from_timestamps(self.yield_timestamp_types(date))

    def _get_event_counts_including(
        self,
        date: dt.date,
        extra: StampType,
    ) -> EventCounts:
        """Return EventCounts object for the given day."""
        timestamps = (*self.yield_timestamp_types(date), extra)
        return EventCounts.from_timestamps(timestamps)

    def _add_timestamp(
        self,
        type_: StampType,
        date: dt.date,
        time: dt.time,
    ) -> None:
        """Add timestamp of given type for given date and time."""
        day = self.days.setdefault(date, [])
        second = time.second
        if time.microsecond > 500:
            second += 1
        day.append(
            Timestamp(type_, time.replace(second=second, microsecond=0)),
        )

    def add_timestamp(
        self,
        type_: StampType,
        datetime: dt.datetime,
    ) -> None:
        """Add timestamp of given time from given datetime."""
        date = datetime.date()
        time = datetime.time()

        # This was a nightmare to figure out how to get it to work
        # properly. Would advise not touching.

        if type_ not in (StampType.AUTO_CHECK_IN, StampType.AUTO_CHECKOUT):
            if type_ == StampType.CHECK_IN:
                events = self.get_event_counts(date)
            else:
                events = self._get_event_counts_including(date, type_)

            if type_ == StampType.CHECKOUT and events.needs_check_in():
                self._add_timestamp(
                    StampType.AUTO_CHECK_IN,
                    date,
                    (datetime - dt.timedelta(minutes=1)).time(),
                )  # datetime.time())
            elif type_ == StampType.CHECK_IN and events.needs_checkout():
                self._add_timestamp(
                    StampType.AUTO_CHECKOUT,
                    date,
                    (datetime - dt.timedelta(minutes=1)).time(),
                )

        self._add_timestamp(type_, date, time)

    def end_of_day_check_missing_stamp(self, date: dt.date) -> None:
        """Add a missing checkout stamp."""
        events = self.get_event_counts(date)

        if events.needs_checkout():
            self._add_timestamp(
                StampType.AUTO_CHECKOUT,
                date,
                dt.time(23, 59, 59),
            )

    def yield_automatic_locations(
        self,
    ) -> Generator[tuple[dt.date, int, dt.time, dt.time]]:
        """Yield (date, index, minimum time, maximum time) tuples of all automatically added timestamps."""
        for date, timestamps in self.days.items():
            prior_time = dt.time()
            for index, timestamp in enumerate(timestamps):
                next_time = timestamp.time
                if timestamp.type_ in (
                    StampType.AUTO_CHECK_IN,
                    StampType.AUTO_CHECKOUT,
                ):
                    yield date, index, prior_time, next_time
                prior_time = next_time

    def replace_timestamp(
        self,
        date: dt.date,
        index: int,
        new_time: dt.time,
    ) -> None:
        """Replace time of a specified timestamp with a new time."""
        if date not in self.days:
            raise KeyError(f"{date = } not recorded")
        assert index > 0
        day = self.days[date]
        old = day[index]

        old_stamp = old.type_

        new_stamp: StampType = old_stamp
        if old_stamp == StampType.AUTO_CHECK_IN:
            new_stamp = StampType.CHECK_IN
        elif old_stamp == StampType.AUTO_CHECKOUT:
            new_stamp = StampType.CHECKOUT

        prior_time = dt.time()
        if index - 1 > 0:
            prior_time = day[index - 1].time

        if prior_time > new_time:
            raise ValueError(
                "new timestamp should be more than previous timestamp",
            )

        if new_time > old.time:
            raise ValueError("new timestamp should be less than old timestamp")

        day[index] = Timestamp(new_stamp, new_time)


class CalendarDatabase(Database[Calendar]):
    """Database of calendar records."""

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
    async with CalendarDatabase("timestamps.json") as database:
        database.data.clear()
        calendar_id = database.add(Calendar())
        calendar = database[calendar_id]
        print(f"{calendar = }")

        calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
        calendar.end_of_day_check_missing_stamp(dt.date.today())
        ##        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
        print("\n".join(map(repr, database.data[0].days[dt.date.today()])))
        if tuple(database.data[0].yield_timestamp_types(dt.date.today())) != (
            StampType.CHECK_IN,
            StampType.CHECKOUT,
            StampType.AUTO_CHECK_IN,
            StampType.CHECKOUT,
            StampType.CHECK_IN,
            StampType.AUTO_CHECKOUT,
        ):
            print("bad")
        print("------")
        database.data[0].days.clear()
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.end_of_day_check_missing_stamp(dt.date.today())
        ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
        print("\n".join(map(repr, database.data[0].days[dt.date.today()])))
        if tuple(database.data[0].yield_timestamp_types(dt.date.today())) != (
            StampType.AUTO_CHECK_IN,
            StampType.CHECKOUT,
            StampType.CHECK_IN,
            StampType.CHECKOUT,
        ):
            print("bad")
        print("------")
        database.data[0].days.clear()
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
        calendar.end_of_day_check_missing_stamp(dt.date.today())
        ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
        print("\n".join(map(repr, database.data[0].days[dt.date.today()])))
        if tuple(database.data[0].yield_timestamp_types(dt.date.today())) != (
            StampType.AUTO_CHECK_IN,
            StampType.CHECKOUT,
            StampType.AUTO_CHECK_IN,
            StampType.CHECKOUT,
        ):
            print("bad")
        print("------")
        database.data[0].days.clear()
        calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
        calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
        calendar.end_of_day_check_missing_stamp(dt.date.today())
        ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
        print("\n".join(map(repr, database.data[0].days[dt.date.today()])))
        if tuple(database.data[0].yield_timestamp_types(dt.date.today())) != (
            StampType.CHECK_IN,
            StampType.AUTO_CHECKOUT,
            StampType.CHECK_IN,
            StampType.AUTO_CHECKOUT,
        ):
            print("bad")

        print(f"{database.data = }")


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    trio.run(run)
