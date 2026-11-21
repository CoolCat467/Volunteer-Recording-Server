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


import bisect
import datetime as dt
from collections import Counter
from dataclasses import dataclass, field, replace
from enum import Enum, IntEnum, auto
from typing import (
    TYPE_CHECKING,
    Any,
    NamedTuple,
    NotRequired,
    Self,
    TypedDict,
    Unpack,
)

import orjson
import trio

from volunteer_recording import security
from volunteer_recording.serializable import (
    Database,
    MappingDatabase,
    Record as Record,
)

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Iterable,
    )
    from os import PathLike


class SerializedUserRecord(TypedDict):
    """Serialized User record."""

    firstname: str
    lastname: str
    date_of_birth: str
    code: int
    retired: NotRequired[bool]
    is_admin: NotRequired[bool]


class UserRecordKwargs(TypedDict, total=False):
    """User record keyword arguments."""

    firstname: str
    lastname: str
    date_of_birth: dt.date
    code: int
    retired: bool
    is_admin: bool


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

    def get_modified_copy(self, **changes: Unpack[UserRecordKwargs]) -> Self:
        """Return new copy given changes."""
        return replace(self, **changes)


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


def time_add_seconds(initial_time: dt.time, seconds: int) -> dt.time:
    """Return new time after adding given number of seconds to it."""
    epoch = dt.date(1970, 1, 1)
    datetime_object = dt.datetime.combine(epoch, initial_time)

    new_datetime = datetime_object + dt.timedelta(seconds=seconds)

    return new_datetime.time()


class BadEntryReason(Enum):
    """Bad entry reason."""

    InvalidInterval = "Start time is after end time."
    FutureEvent = "Interval would happen in the future."
    IntervalCollision = "Intersects with an existing interval."


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
                for k, v in dict_.get("days", {}).items()
            },
        )

    def get_timestamp(self, date: dt.date, index: int) -> Timestamp | None:
        """Return a specific timestamp given the date and index or None if not exists."""
        day = self.days.get(date)
        if day is None:
            return None
        if index < 0 or index >= len(day):
            return None
        return day[index]

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

    def _append_timestamp(
        self,
        type_: StampType,
        date: dt.date,
        time: dt.time,
    ) -> None:
        """Add timestamp of given type for given date and time."""
        day = self.days.setdefault(date, [])
        day.append(
            Timestamp(type_, time.replace(microsecond=0)),
        )

    def get_prior_timestamp_time(
        self,
        date: dt.date,
        index: int,
    ) -> dt.time:
        """Return the time of the event before the given index on the specified day."""
        if date not in self.days:
            return dt.time()
        day = self.days[date]

        if index - 1 >= 0:
            return day[index - 1].time
        return dt.time()

    @staticmethod
    def _get_end_time(date: dt.date) -> dt.time:
        """Return end time cutoff for a given day."""
        if date == dt.date.today():
            return dt.datetime.now().time().replace(microsecond=0)
        return dt.time(23, 59, 59)

    def get_next_timestamp_time(
        self,
        date: dt.date,
        index: int,
    ) -> dt.time:
        """Return the time of the event before the given index on the specified day."""
        if date not in self.days:
            return self._get_end_time(date)
        day = self.days[date]

        if index + 1 < len(day):
            return day[index + 1].time
        return self._get_end_time(date)

    def get_last_timestamp_time(
        self,
        date: dt.date,
    ) -> dt.time | None:
        """Return the time of the last timestamp for a given day or None if there are no recorded timestamps."""
        day = self.days.get(date)
        if day is None:
            return None

        return self.get_prior_timestamp_time(date, len(day))

    def add_timestamp(
        self,
        type_: StampType,
        datetime: dt.datetime,
    ) -> tuple[dt.date, StampType] | None:
        """Add timestamp of given time from given datetime."""
        date = datetime.date()
        time = datetime.time()

        # This was a nightmare to figure out how to get it to work
        # properly. Would advise not touching.

        auto_event: tuple[dt.date, StampType] | None = None

        if type_ not in (StampType.AUTO_CHECK_IN, StampType.AUTO_CHECKOUT):
            if type_ == StampType.CHECK_IN:
                events = self.get_event_counts(date)
            else:
                events = self._get_event_counts_including(date, type_)

            last_time = self.get_last_timestamp_time(date)
            if last_time is None:
                prior_time = dt.time()
            else:
                prior_time = time_add_seconds(last_time, 1)

            if type_ == StampType.CHECKOUT and events.needs_check_in():
                self._append_timestamp(
                    StampType.AUTO_CHECK_IN,
                    date,
                    prior_time,
                )
                auto_event = date, StampType.AUTO_CHECK_IN
            elif type_ == StampType.CHECK_IN and events.needs_checkout():
                self._append_timestamp(
                    StampType.AUTO_CHECKOUT,
                    date,
                    prior_time,
                )
                auto_event = date, StampType.AUTO_CHECKOUT

        self._append_timestamp(type_, date, time)
        return auto_event

    def end_of_day_check_missing_stamp(
        self,
        date: dt.date,
    ) -> tuple[dt.date, StampType] | None:
        """Add a missing checkout stamp."""
        events = self.get_event_counts(date)

        if events.needs_checkout():
            self._append_timestamp(
                StampType.AUTO_CHECKOUT,
                date,
                dt.time(23, 59, 59),
            )
            return date, StampType.AUTO_CHECKOUT
        return None

    def yield_interval_data(
        self,
        date: dt.date,
    ) -> Generator[tuple[Timestamp, Timestamp]]:
        """Yield (start Timestamp, end Timestamp) tuples for the given day."""
        timestamps = self.days.get(date, ())
        start: Timestamp
        for index, timestamp in enumerate(timestamps):
            if not index & 1:
                if timestamp.type_ not in (
                    StampType.CHECK_IN,
                    StampType.AUTO_CHECK_IN,
                ):
                    raise RuntimeError(
                        f"Corrupted time interval {timestamp = }",
                    )
                start = timestamp
            else:
                if timestamp.type_ not in (
                    StampType.CHECKOUT,
                    StampType.AUTO_CHECKOUT,
                ):
                    raise RuntimeError(
                        f"Corrupted time interval {timestamp = }",
                    )
                yield (start, timestamp)
        if len(timestamps) % 2 != 0:
            # missing end entry that should have been added by
            # end_of_day_check_missing_stamp, presumably the current
            # date is today and it hasn't run yet.
            end = Timestamp(StampType.AUTO_CHECKOUT, self._get_end_time(date))
            yield (start, end)

    def get_interval_data(
        self,
        date: dt.date,
        target_interval_index: int,
    ) -> tuple[Timestamp, Timestamp] | None:
        """Return (start Timestamp, end Timestamp) tuple for a given interval on a given day."""
        for index, (start, end) in enumerate(self.yield_interval_data(date)):
            if index == target_interval_index:
                return (start, end)
        return None

    def yield_interval_time_data(
        self,
        date: dt.date,
    ) -> Generator[tuple[dt.time, dt.time]]:
        """Yield (start time, end time) tuples for the given day."""
        for start, end in self.yield_interval_data(date):
            yield (start.time, end.time)

    def _insert_timestamp(
        self,
        type_: StampType,
        date: dt.date,
        time: dt.time,
    ) -> None:
        """Insert timestamp of given type for given date and time."""
        day = self.days.setdefault(date, [])
        new_timestamp = Timestamp(type_, time.replace(microsecond=0))
        # bisect.insort(day, new_timestamp, key=lambda ts: ts.time)
        bisect.insort(
            day,
            new_timestamp,
            key=lambda ts: (
                ts.time,
                ts.type_ in (StampType.CHECK_IN, StampType.AUTO_CHECK_IN),
            ),
        )

    def check_entry_collisions(
        self,
        date: dt.date,
        start_time: dt.time,
        end_time: dt.time,
    ) -> BadEntryReason | None:
        """Return BadEntryReason if the new entry is invalid or overlaps an existing interval."""
        if end_time <= start_time:
            return BadEntryReason.InvalidInterval

        today = dt.date.today()
        if date > today:
            # Adding events for the future could cause problems when new
            # events are added later
            return BadEntryReason.FutureEvent

        if date == today and end_time > dt.datetime.now().time():
            # Again, future could cause problems.
            return BadEntryReason.FutureEvent

        # Also problems if there is any overlap between existing intervals.
        for start, end in self.yield_interval_time_data(date):
            if start_time < end and start < end_time:
                return BadEntryReason.IntervalCollision

        # Went all the way through, then things should be fine.
        return None

    def insert_manual_entry(
        self,
        date: dt.date,
        start_time: dt.time,
        end_time: dt.time,
    ) -> None:
        """Insert a manual entry. Raises ValueError if the entry is invalid or overlaps."""
        bad_interval_reason = self.check_entry_collisions(
            date,
            start_time,
            end_time,
        )
        if bad_interval_reason is not None:
            raise ValueError(bad_interval_reason.value)

        self._insert_timestamp(StampType.CHECK_IN, date, start_time)
        self._insert_timestamp(StampType.CHECKOUT, date, end_time)

    @staticmethod
    def interval_index_to_day_index(
        interval_index: int,
        is_checkout: bool,
    ) -> int:
        """Return day index from interval index and if you want the checkout or check-in timestamp."""
        return interval_index * 2 + is_checkout

    def yield_automatic_locations(
        self,
        date: dt.date,
    ) -> Generator[tuple[int, dt.time, dt.time]]:
        """Yield (index, minimum time, maximum time) tuples of all automatically added timestamps from a given date."""
        timestamps = self.days.get(date, ())
        prior_time = dt.time()
        for index, timestamp in enumerate(timestamps):
            next_time = timestamp.time
            if timestamp.type_ in (
                StampType.AUTO_CHECK_IN,
                StampType.AUTO_CHECKOUT,
            ):
                yield index, prior_time, next_time
            prior_time = next_time

    def get_automatic_location_range(
        self,
        date: dt.date,
        target_index: int,
    ) -> tuple[dt.time, dt.time] | None:
        """Return (minimum time, maximum time) tuple from automatically added timestamp given target index and date."""
        for index, start, end in self.yield_automatic_locations(date):
            if index == target_index:
                return (start, end)
        return None

    def yield_all_automatic_locations(
        self,
    ) -> Generator[tuple[dt.date, tuple[int, dt.time, dt.time]]]:
        """Yield (date, (index, minimum time, maximum time)) tuples of all automatically added timestamps."""
        for date in self.days:
            for event in self.yield_automatic_locations(date):
                yield date, event

    def yield_unresolved_events(
        self,
    ) -> Generator[tuple[dt.date, StampType]]:
        """Yield (date, StampType) tuples for all unresolved events."""
        for date, timestamps in self.days.items():
            for timestamp in timestamps:
                if timestamp.type_ in (
                    StampType.AUTO_CHECK_IN,
                    StampType.AUTO_CHECKOUT,
                ):
                    yield date, timestamp.type_

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

        prior_time = self.get_prior_timestamp_time(date, index)
        next_time = self.get_next_timestamp_time(date, index)

        if prior_time > new_time:
            raise ValueError(
                "new timestamp should be more than previous timestamp",
            )

        if new_time > next_time:
            raise ValueError(
                "new timestamp should be less than next timestamp",
            )

        day[index] = Timestamp(new_stamp, new_time)

    def delete_interval(
        self,
        date: dt.date,
        interval_index: int,
    ) -> None:
        """Delete a specified interval."""
        if date not in self.days:
            raise KeyError(f"{date = } not recorded")
        day = self.days[date]

        index = self.interval_index_to_day_index(interval_index, False)
        if index < 0 or index + 1 >= len(day):
            raise ValueError("interval index out of range")

        assert day[index].type_ in (
            StampType.CHECK_IN,
            StampType.AUTO_CHECK_IN,
        )
        assert day[index + 1].type_ in (
            StampType.CHECKOUT,
            StampType.AUTO_CHECKOUT,
        )

        del day[index + 1]
        del day[index]


class CalendarDatabase(Database[Calendar]):
    """Database of calendar records."""

    __slots__ = ()

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

    def yield_all_unresolved_events(
        self,
    ) -> Generator[tuple[int, tuple[dt.date, StampType]]]:
        """Yield (user_id, (date, stamp type)) automatic event tuples."""
        for user_id, calendar in enumerate(self):
            for event in calendar.yield_unresolved_events():
                yield user_id, event


##    def yield_all_events


class PasswordDatabase(MappingDatabase[int, str]):
    """Database of password records."""

    __slots__ = ("pepper",)

    def __init__(self, path: PathLike[str] | str, pepper: str) -> None:  # noqa: D107
        super().__init__(path)
        self.pepper = pepper

    def deserialize_key(self, key: str) -> int:  # noqa: D102
        return int(key)

    def deserialize_entry(self, entry: str) -> str:  # noqa: D102
        return entry

    def serialize(self) -> bytes:
        """Return serialized data to write to file."""
        return orjson.dumps(
            self.data,
            option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_NON_STR_KEYS,
        )

    def set_password(self, user_id: int, new_password: str) -> None:
        """Set password for given user id to new password."""
        self[user_id] = security.create_new_login_credentials(
            new_password,
            self.pepper,
        )

    async def check_password(self, user_id: int, password: str) -> bool:
        """Return if given password is correct for given user."""
        record = self.get(user_id)
        if record is None:
            raise KeyError("user not found")
        return await security.compare_hash(password, record, self.pepper)


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
    # async with CalendarDatabase("timestamps.json") as database:
    calendar = Calendar()
    print(f"{calendar = }")

    calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
    calendar.end_of_day_check_missing_stamp(dt.date.today())
    ##        calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
    print("\n".join(map(repr, calendar.days[dt.date.today()])))
    if tuple(calendar.yield_timestamp_types(dt.date.today())) != (
        StampType.CHECK_IN,
        StampType.CHECKOUT,
        StampType.AUTO_CHECK_IN,
        StampType.CHECKOUT,
        StampType.CHECK_IN,
        StampType.AUTO_CHECKOUT,
    ):
        print("bad")
    print("------")
    calendar.days.clear()
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.end_of_day_check_missing_stamp(dt.date.today())
    ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
    print("\n".join(map(repr, calendar.days[dt.date.today()])))
    if tuple(calendar.yield_timestamp_types(dt.date.today())) != (
        StampType.AUTO_CHECK_IN,
        StampType.CHECKOUT,
        StampType.CHECK_IN,
        StampType.CHECKOUT,
    ):
        print("bad")
    print("------")
    calendar.days.clear()
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECKOUT, dt.datetime.now())
    calendar.end_of_day_check_missing_stamp(dt.date.today())
    ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
    print("\n".join(map(repr, calendar.days[dt.date.today()])))
    if tuple(calendar.yield_timestamp_types(dt.date.today())) != (
        StampType.AUTO_CHECK_IN,
        StampType.CHECKOUT,
        StampType.AUTO_CHECK_IN,
        StampType.CHECKOUT,
    ):
        print("bad")
    print("------")
    calendar.days.clear()
    calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
    calendar.add_timestamp(StampType.CHECK_IN, dt.datetime.now())
    calendar.end_of_day_check_missing_stamp(dt.date.today())
    ##        print("\n".join(map(repr, database.data[0].yield_timestamp_types(dt.date.today()))))
    print("\n".join(map(repr, calendar.days[dt.date.today()])))
    if tuple(calendar.yield_timestamp_types(dt.date.today())) != (
        StampType.CHECK_IN,
        StampType.AUTO_CHECKOUT,
        StampType.CHECK_IN,
        StampType.AUTO_CHECKOUT,
    ):
        print("bad")


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    trio.run(run)
