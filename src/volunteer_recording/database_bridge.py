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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

import trio

from volunteer_recording.serializable import Database, Record as Record

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Mapping,
    )


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
    def deserialize(cls, dict_: Mapping[str, Any]) -> Self:
        """Return new class instance from deserializing dictionary."""
        kwargs = dict(dict_)
        kwargs["date_of_birth"] = dt.date.fromisoformat(dict_["date_of_birth"])

        return cls(**kwargs)


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


async def run() -> None:
    """Run program."""
    async with UserDatabase("test.json") as database:
        database.data.clear()
        user = User(
            "Firstname",
            "Lastname",
            dt.date(2000, 1, 1),
            1234,
        )
        print(f"{user = }")
        print(f"{tuple(database) = }")

        database.add(user)
        print(f"{tuple(database) = }")


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    trio.run(run)
