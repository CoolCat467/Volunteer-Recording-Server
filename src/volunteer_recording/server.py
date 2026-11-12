"""Volunteer Recording Webserver - Webserver to help keep track of volunteer hours.

Copyright (C) 2026  CoolCat467

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

__title__ = "Volunteer Recording Webserver"
__author__ = "CoolCat467"
__version__ = "1.0.0"
__license__ = "GNU General Public License Version 3"


import argparse
import datetime as dt
import tomllib
import traceback
from collections.abc import (
    AsyncIterator,
    Coroutine,
    Iterable,
)
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from os import getenv
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    TypedDict,
)
from urllib.parse import urlencode
from uuid import UUID, uuid4

import platformdirs
import trio
from dotenv import load_dotenv
from hypercorn.config import Config
from hypercorn.trio import serve
from quart import request
from quart.templating import stream_template
from quart_auth import (
    AuthUser,
    QuartAuth,
    Unauthorized,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from quart_trio import QuartTrio

from volunteer_recording import database_bridge
from volunteer_recording.elapsed import combine_end
from volunteer_recording.server_utils import (
    find_ip,
    get_exception_page,
    pretty_exception,
)

if TYPE_CHECKING:
    from typing import ParamSpec

    from werkzeug import Response as WerkzeugResponse

    PS = ParamSpec("PS")

FILE_TITLE: Final = __title__.lower().replace(" ", "-").replace("-", "_")
CONFIG_PATH: Final = trio.Path(
    platformdirs.user_config_path(FILE_TITLE, __author__),
)
DATA_PATH: Final = trio.Path(
    platformdirs.user_data_path(FILE_TITLE, __author__),
)
CACHE_PATH: Final = trio.Path(
    platformdirs.user_cache_path(FILE_TITLE, __author__),
)
MAIN_CONFIG: Final = CONFIG_PATH / "config.toml"
USER_DATA: Final = DATA_PATH / "user.json"
CALENDAR_DATA: Final = DATA_PATH / "calendar.json"
PASSWORD_DATA: Final = DATA_PATH / "password.json"

load_dotenv()
PEPPER: Final = getenv("COOKIE_SECRET", "")


def datetime_now_tomorrow() -> dt.datetime:
    """Return datetime of one day from now."""
    return dt.datetime.now(dt.UTC) + dt.timedelta(days=1)


@dataclass(slots=True, frozen=True)
class Session:
    """Session data."""

    user_id: int
    expires: dt.datetime = field(default_factory=datetime_now_tomorrow)


@dataclass(slots=True, frozen=True)
class SessionDatabase:
    """Session database."""

    sessions: dict[UUID, Session] = field(default_factory=dict)

    def add_session(self, session: Session) -> UUID:
        """Return UUID of new session after adding it to the database."""
        uuid = uuid4()
        self.sessions[uuid] = session
        return uuid

    def create_session(self, user_id: int) -> UUID:
        """Return UUID of new session for given user id."""
        session = Session(user_id)
        return self.add_session(session)

    def find_session_uuid(self, uuid: UUID) -> Session | None:
        """Return session from uuid or return None on failure."""
        return self.sessions.get(uuid)

    def find_session_user_id(
        self,
        user_id: int,
    ) -> tuple[UUID, Session] | None:
        """Return session from user id or None on failure."""
        for uuid, session in self.sessions.items():
            if session.user_id == user_id:
                return uuid, session
        return None


class AppData(TypedDict):
    """Global shared application data."""

    user: database_bridge.UserDatabase
    calendar: database_bridge.CalendarDatabase
    password: database_bridge.PasswordDatabase
    session: SessionDatabase


app: Final = QuartTrio(  # pylint: disable=invalid-name
    __name__,
    static_folder="static",
    template_folder="templates",
)
QuartAuth(app)
APP_DATA = AppData(
    user=database_bridge.UserDatabase(USER_DATA),
    calendar=database_bridge.CalendarDatabase(CALENDAR_DATA),
    password=database_bridge.PasswordDatabase(PASSWORD_DATA, PEPPER),
    session=SessionDatabase(),
)


@app.get("/")
async def root_get() -> AsyncIterator[str]:
    """Handle main page GET request."""
    return await stream_template(
        "root.html.jinja",
    )


class SelectUserType(Enum):
    """Select user type."""

    CHECK_IN = "/check-in"
    CHECK_OUT = "/check-out"
    ADMIN_LOGIN = "/admin-login"


def get_select_type_from_endpoint(endpoint: str) -> SelectUserType:
    """Return select user type from endpoint name."""
    if endpoint.startswith("check_in"):
        return SelectUserType.CHECK_IN
    if endpoint.startswith("check_out"):
        return SelectUserType.CHECK_OUT
    if endpoint.startswith("admin_login"):
        return SelectUserType.ADMIN_LOGIN

    assert len(SelectUserType) == 3
    raise NotImplementedError(endpoint)


def get_select_type_from_full_path(full_path: str) -> SelectUserType:
    """Return select user type from endpoint name."""
    parts = full_path.removeprefix("/").removesuffix("?").split("/", 1)
    return SelectUserType(f"/{parts[0]}")


@app.get(SelectUserType.CHECK_IN.value, endpoint="check_in_get")
@app.get(SelectUserType.CHECK_OUT.value, endpoint="check_out_get")
@app.get(SelectUserType.ADMIN_LOGIN.value, endpoint="admin_login_get")
@pretty_exception
async def phone_input_get() -> AsyncIterator[str]:
    """Render the phone input page."""
    return await stream_template("phone_input.html.jinja")


@app.post(SelectUserType.CHECK_IN.value, endpoint="check_in_post")
@app.post(SelectUserType.CHECK_OUT.value, endpoint="check_out_post")
@app.post(SelectUserType.ADMIN_LOGIN.value, endpoint="admin_login_post")
@pretty_exception
async def phone_input_post() -> (
    tuple[AsyncIterator[str], int] | WerkzeugResponse
):
    """Handle phone digits POST request."""
    multi_dict = await request.form
    form = multi_dict.to_dict()

    digits = form.get("digits")

    source_page = request.full_path.removesuffix("?")

    errors = []
    if not digits:
        errors.append("Missing <code>digits</code> field.")
    if not isinstance(digits, str):
        errors.append("<code>digits</code> field type must be a string.")
    elif len(digits) != 4:
        errors.append(
            "<code>digits</code> field must be exactly 4 characters long.",
        )
    elif not digits.isdecimal():
        errors.append("<code>digits</code> field value must be a decimal.")
    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=source_page,
        )

    assert isinstance(digits, str)

    code = int(digits)
    params = urlencode({"digits": f"{code:04}"})
    return app.redirect(f"{source_page}/select-user?{params}")


async def stream_select_user(
    code: int,
    return_link: str,
    is_admin: bool = False,
) -> AsyncIterator[str]:
    """Return select user template stream."""
    # Get user from code
    if is_admin:
        user_records = APP_DATA["user"].yield_admin_records_from_code(
            code=code,
        )
    else:
        user_records = APP_DATA["user"].yield_records_from_code(code=code)

    return await stream_template(
        "select_user.html.jinja",
        user_records=user_records,
        return_link=return_link,
        show_create=not is_admin,
    )


@app.get(
    f"{SelectUserType.CHECK_IN.value}/select-user",
    endpoint="check_in_select_user_get",
)
@app.get(
    f"{SelectUserType.CHECK_OUT.value}/select-user",
    endpoint="check_out_select_user_get",
)
@app.get(
    f"{SelectUserType.ADMIN_LOGIN.value}/select-user",
    endpoint="admin_login_select_user_get",
)
@pretty_exception
async def select_user_get() -> (
    tuple[AsyncIterator[str], int] | AsyncIterator[str]
):
    """Handle select user GET request."""
    args = request.args.to_dict()

    digits = args.get("digits")

    select_type = get_select_type_from_full_path(request.full_path)

    errors = []
    if not digits:
        errors.append("Missing <code>digits</code> argument.")
    elif len(digits) != 4:
        errors.append(
            "<code>digits</code> argument must be exactly 4 characters long.",
        )
    elif not digits.isdecimal():
        errors.append("<code>digits</code> argument value must be a decimal.")
    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=select_type.value,
        )

    assert digits is not None

    is_admin = select_type == SelectUserType.ADMIN_LOGIN

    return await stream_select_user(
        code=int(digits),
        return_link=select_type.value,
        is_admin=is_admin,
    )


@app.post(
    f"{SelectUserType.CHECK_IN.value}/select-user",
    endpoint="check_in_select_user_post",
)
@app.post(
    f"{SelectUserType.CHECK_OUT.value}/select-user",
    endpoint="check_out_select_user_post",
)
@app.post(
    f"{SelectUserType.ADMIN_LOGIN.value}/select-user",
    endpoint="admin_login_select_user_post",
)
@pretty_exception
async def select_user_post() -> (
    tuple[AsyncIterator[str], int] | WerkzeugResponse
):
    """Handle select user POST request."""
    multi_dict = await request.form
    form = multi_dict.to_dict()
    args = request.args.to_dict()

    create_user = "create_user" in form
    digits = args.get("digits")
    user_id = form.get("user_id")

    select_type = get_select_type_from_full_path(request.full_path)
    create_available = select_type != SelectUserType.ADMIN_LOGIN

    action_create = create_user and create_available
    source_page = select_type.value

    errors = []
    if action_create and digits:
        if len(digits) != 4:
            errors.append(
                "<code>digits</code> argument must be exactly 4 characters long.",
            )
        elif not digits.isdecimal():
            errors.append(
                "<code>digits</code> argument value must be a decimal.",
            )
    else:
        if not isinstance(user_id, str):
            errors.append("<code>user_id</code> field type must be a string.")
        elif not user_id.isdecimal():
            errors.append(
                "<code>user_id</code> field value must be a decimal.",
            )
    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=request.full_path.removesuffix("?"),
        )

    if action_create:
        params_dict = {}
        if digits is not None:
            params_dict["digits"] = f"{int(digits):04}"

        params = urlencode(params_dict)
        extra = f"?{params}" if params else ""
        return app.redirect(f"{source_page}/create-user{extra}")

    assert user_id is not None
    numeric_user_id = int(user_id)

    return app.redirect(f"{source_page}/user/{numeric_user_id}")


@app.get(
    f"{SelectUserType.CHECK_IN.value}/create-user",
    endpoint="check_in_create_user_get",
)
@app.get(
    f"{SelectUserType.CHECK_OUT.value}/create-user",
    endpoint="check_out_create_user_get",
)
@pretty_exception
async def create_user_get() -> (
    tuple[AsyncIterator[str], int] | AsyncIterator[str]
):
    """Handle create user GET request."""
    args = request.args.to_dict()

    digits = args.get("digits")

    select_type = get_select_type_from_full_path(request.full_path)
    source_page = select_type.value

    errors = []
    if digits is not None:
        if len(digits) != 4:
            errors.append(
                "<code>digits</code> argument must be exactly 4 characters long.",
            )
        elif not digits.isdecimal():
            errors.append(
                "<code>digits</code> argument value must be a decimal.",
            )
    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=source_page,
        )

    autofill_digits: int | None = None
    if digits is not None:
        autofill_digits = int(digits)

    return await stream_template(
        "create_user.html.jinja",
        return_link=f"{source_page}/select-user?digits={autofill_digits:04}",
        # autofill_firstname=autofill_firstname,
        # autofill_lastname=autofill_lastname,
        # autofill_birthday=autofill_birthday,
        autofill_digits=f"{autofill_digits:04}",
    )


def parse_iso_date(string: str) -> dt.date | None:
    """Return date object from string or None on error."""
    try:
        return dt.date.fromisoformat(string)
    except ValueError:
        return None


def create_new_user(
    firstname: str,
    lastname: str,
    date_of_birth: dt.date,
    code: int,
) -> int:
    """Return new user id from creating user."""
    user_db = APP_DATA["user"]
    calendar_db = APP_DATA["calendar"]

    if len(user_db) != len(calendar_db):
        raise RuntimeError(
            "number of user records does not match number of calendar records",
        )

    user_id = user_db.add(
        database_bridge.User(
            firstname=firstname,
            lastname=lastname,
            date_of_birth=date_of_birth,
            code=code,
        ),
    )

    user_id2 = calendar_db.add(database_bridge.Calendar())
    assert user_id == user_id2

    return user_id


@app.post(
    f"{SelectUserType.CHECK_IN.value}/create-user",
    endpoint="check_in_create_user_post",
)
@app.post(
    f"{SelectUserType.CHECK_OUT.value}/create-user",
    endpoint="check_out_create_user_post",
)
@pretty_exception
async def create_user_post() -> (
    tuple[AsyncIterator[str], int] | AsyncIterator[str]
):
    """Handle create user POST request."""
    multi_dict = await request.form
    form = multi_dict.to_dict()

    firstname = form.get("firstname")
    lastname = form.get("lastname")
    date_of_birth = form.get("date_of_birth")
    digits = form.get("digits")

    select_type = get_select_type_from_full_path(request.full_path)

    errors = []
    if not firstname:
        errors.append("Missing <code>firstname</code> field.")
    elif not isinstance(firstname, str):
        errors.append("<code>firstname</code> field type must be a string.")
    elif len(firstname) < 2:
        errors.append(
            "<code>firstname</code> field must be at least 2 characters long.",
        )
    elif len(firstname) > 100:
        errors.append(
            "<code>firstname</code> field must be at most 100 characters long.",
        )

    if not lastname:
        errors.append("Missing <code>lastname</code> field.")
    elif not isinstance(lastname, str):
        errors.append("<code>lastname</code> field type must be a string.")
    elif len(lastname) < 2:
        errors.append(
            "<code>lastname</code> field must be at least 2 characters long.",
        )
    elif len(lastname) > 100:
        errors.append(
            "<code>lastname</code> field must be at most 100 characters long.",
        )

    if not date_of_birth:
        errors.append("Missing <code>date_of_birth</code> field.")
    elif not isinstance(date_of_birth, str):
        errors.append(
            "<code>date_of_birth</code> field type must be a string.",
        )
    elif parse_iso_date(date_of_birth) is None:
        errors.append(
            "<code>date_of_birth</code> field type must be an ISO date.",
        )

    if not digits:
        errors.append("Missing <code>digits</code> field.")
    elif not isinstance(digits, str):
        errors.append("<code>digits</code> field type must be a string.")
    elif len(digits) != 4:
        errors.append(
            "<code>digits</code> field must be exactly 4 characters long.",
        )
    elif not digits.isdecimal():
        errors.append("<code>digits</code> field value must be a decimal.")

    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=request.full_path.removesuffix("?"),
        )

    assert firstname is not None
    assert lastname is not None
    assert date_of_birth is not None
    assert digits is not None

    date_of_birth_date = dt.date.fromisoformat(date_of_birth)
    assert date_of_birth_date is not None
    numeric_digits = int(digits)

    user_id = create_new_user(
        firstname,
        lastname,
        date_of_birth_date,
        numeric_digits,
    )

    if select_type == SelectUserType.CHECK_IN:
        return await check_in_user_get(user_id, created_user=True)
    if select_type == SelectUserType.CHECK_OUT:
        return await check_out_user_get(user_id, created_user=True)

    raise NotImplementedError(f"{request.endpoint = }")


def user_add_timestamp(
    user_id: int,
    type_: database_bridge.StampType = database_bridge.StampType.CHECK_IN,
) -> None:
    """Add a timestamp for the given user. User ID must be valid."""
    calendar_db = APP_DATA["calendar"]
    user_calendar = calendar_db[user_id]

    user_calendar.add_timestamp(
        database_bridge.StampType.CHECK_IN,
        dt.datetime.now(dt.UTC),
    )


async def check_in_user_get(
    user_id: int,
    created_user: bool = False,
) -> AsyncIterator[str]:
    """Handle user check-in GET request."""
    # User id exists, checked in user_selected_get

    # Add check-in stamp for user
    user_add_timestamp(user_id, database_bridge.StampType.CHECK_IN)

    message = "Successfully checked in!"
    if created_user:
        message = "Successfully created new user and checked in!"

    return await stream_template(
        "success.html.jinja",
        message=message,
        # refreshes_after=10,
    )


async def check_out_user_get(
    user_id: int,
    created_user: bool = False,
) -> AsyncIterator[str]:
    """Handle user check-out GET request."""
    # User id exists, checked in user_selected_get

    # TODO: category, for now just do checkout

    # Add check-in stamp for user
    user_add_timestamp(user_id, database_bridge.StampType.CHECKOUT)

    message = "Successfully checked out!"
    if created_user:
        message = "Successfully created new user and checked out!"

    return await stream_template(
        "success.html.jinja",
        message=message,
        # refreshes_after=10,
    )


async def admin_login_user_get(
    user_id: int,
    is_admin: bool,
) -> tuple[AsyncIterator[str], int] | AsyncIterator[str]:
    """Handle user administrator login GET request."""
    # User id exists, checked in user_selected_get

    if not is_admin:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "User is not an administrator.",
            return_link="/admin-login",
        )

    bad_password = request.args.get("bad_password") is not None

    error_message: str | None = None
    if bad_password:
        error_message = "Given password was incorrect."

    return await stream_template(
        "prompt_password.html.jinja",
        error_message=error_message,
    )


@app.get(
    f"{SelectUserType.CHECK_IN.value}/user/<int:user_id>",
    endpoint="check_in_user_get",
)
@app.get(
    f"{SelectUserType.CHECK_OUT.value}/user/<int:user_id>",
    endpoint="check_out_user_get",
)
@app.get(
    f"{SelectUserType.ADMIN_LOGIN.value}/user/<int:user_id>",
    endpoint="admin_login_user_get",
)
@pretty_exception
async def user_selected_get(
    user_id: int,
) -> tuple[AsyncIterator[str], int] | AsyncIterator[str]:
    """Handle user selected GET request."""
    user = APP_DATA["user"].get(user_id)

    select_type = get_select_type_from_full_path(request.full_path)
    source_url = select_type.value

    if user is None:
        return await get_exception_page(
            404,  # not found
            "Not Found",
            "User not found.",
            return_link=source_url,
        )

    if request.endpoint == "check_in_user_get":
        return await check_in_user_get(user_id)
    if request.endpoint == "check_out_user_get":
        return await check_out_user_get(user_id)
    if request.endpoint == "admin_login_user_get":
        return await admin_login_user_get(user_id, user.is_admin)

    # Should be unreachable
    raise NotImplementedError(f"{request.endpoint = }")


async def check_password_correct(user_id: int, password: str) -> bool:
    """Return if given password is correct for given user."""
    password_db = APP_DATA["password"]
    return await password_db.check_password(user_id, password)


def perform_login_user(user_id: int) -> UUID:
    """Return session UUID after performing login user."""
    session_db = APP_DATA["session"]
    uuid = session_db.create_session(user_id)
    login_user(AuthUser(str(uuid)))
    return uuid


def get_user_id_from_session() -> int:
    """Return user id from session. If not found, logout and raise Unauthorized."""
    assert current_user.is_authenticated
    session_db = APP_DATA["session"]
    session = session_db.find_session_uuid(UUID(current_user.auth_id))
    if session is None:
        logout_user()
        raise Unauthorized()
    return session.user_id


@app.post(f"{SelectUserType.ADMIN_LOGIN.value}/user/<int:user_id>")
@pretty_exception
async def admin_login_user_post(
    user_id: int,
) -> tuple[AsyncIterator[str], int] | WerkzeugResponse:
    """Handle user administrator login POST request."""
    user = APP_DATA["user"].get(user_id)

    if user is None:
        return await get_exception_page(
            404,  # not found
            "Not Found",
            "User not found.",
            return_link=SelectUserType.ADMIN_LOGIN.value,
        )

    multi_dict = await request.form
    form = multi_dict.to_dict()

    password = form.get("password")

    errors = []
    if not password:
        errors.append("Missing <code>password</code> field.")
    elif not isinstance(password, str):
        errors.append(
            "<code>password</code> field type must be a string.",
        )

    if errors:
        return await get_exception_page(
            400,  # bad request
            "Bad Request",
            "\n<br>\n".join(errors),
            return_link=request.full_path.removesuffix("?"),
        )

    assert password is not None

    if not await check_password_correct(user_id, password):
        return app.redirect(f"{request.path}?bad_password=1")

    perform_login_user(user_id)

    return app.redirect("/admin")


@app.get("/admin")
@pretty_exception
@login_required
async def handle_admin_get() -> AsyncIterator[str]:
    """Handle administrator root GET request."""
    print(f"{current_user.auth_id = }")
    logout_user()
    raise NotImplementedError(f"{current_user.auth_id = }")


def admin_reset_password(user_id: int, password: str) -> None:
    """Set the password for given user to given value."""
    password_db = APP_DATA["password"]
    password_db.set_password(user_id, password)


def grant_admin_privileges(user_id: int, password: str) -> None:
    """Grant admin privileges to given user and set their password."""
    user_db = APP_DATA["user"]
    user_db[user_id] = user_db[user_id].get_modified_copy(is_admin=True)

    admin_reset_password(user_id, password)


##@app.post("/")
##@pretty_exception
##async def root_post() -> str | tuple[AsyncIterator[str], int]:
##    """Handle page POST."""
##    multi_dict = await request.form
##    form = multi_dict.to_dict()
##
##    character_card = form.get("character_card", "").strip()
##    current_situation = form.get("current_situation", "").strip()
##
##    errors = []
##    if not character_card:
##        errors.append("Missing <code>character_card</code> parameter.")
##    if not current_situation:
##        errors.append("Missing <code>current_situation</code> parameter.")
##    if errors:
##        return await get_exception_page(
##            400,  # bad request
##            "Bad Request",
##            "\n<br>\n".join(errors),
##            request.url,
##        )
##
##    return "Not Implemented kekw"


##@app.get("/character_response/<uuid:response_uuid>")
##@pretty_exception
##async def character_response_get(
##    response_uuid: UUID,
##) -> tuple[str, int]:
##    """Character response page get handling."""
##    # page expired
##    return "Requested page is expired or invalid.", 410


def ask_integer(prompt: str | None = None) -> int:
    """Return integer from user input."""
    while True:
        if prompt is not None:
            print(prompt)
        result = input("> ")
        try:
            return int(result)
        except ValueError:
            print("Invalid input, enter an integer.")


def ask_date(select: str = "Current ") -> tuple[int, int, int]:
    """Return year, month, day tuple."""
    if select and not select.endswith(" "):
        select += " "
    year = ask_integer(f"Enter {select}Year")
    month = ask_integer(f"Enter {select}Month")
    day = ask_integer(f"Enter {select}Day")
    return (year, month, day)


def create_user_console() -> int:
    """Return user id from creating a new user from user input."""
    user_id = create_new_user(
        input("Enter firstname: "),
        input("Enter lastname: "),
        dt.date(*ask_date("date of birth ")),
        ask_integer("Enter last 4 digits of phone number"),
    )
    print(f"Created new user ({user_id = })")
    return user_id


async def async_run_server(
    serve_partial: partial[Coroutine[Any, Any, None]],
) -> None:
    """Call server partial while managing databases."""
    async with APP_DATA["user"], APP_DATA["calendar"], APP_DATA["password"]:
        if len(APP_DATA["user"]) != len(APP_DATA["calendar"]):
            raise RuntimeError(
                "number of user records does not match number of calendar records",
            )
        if not APP_DATA["user"]:
            grant_admin_privileges(
                create_new_user("Admin", "N/A", dt.date.today(), 0),
                "admin",
            )
            print("Created admin user with password `admin`")
        async with trio.open_nursery() as nursery:
            nursery.start_soon(serve_partial)


def run_server(
    secure_bind_port: int | None = None,
    insecure_bind_port: int | None = None,
    ip_addr: str | None = None,
    hypercorn: dict[str, object] | None = None,
) -> None:
    """Asynchronous Entry Point."""
    if secure_bind_port is None and insecure_bind_port is None:
        raise ValueError(
            "Port must be specified with `port` and or `ssl_port`!",
        )

    if not ip_addr:
        ip_addr = find_ip()

    if not hypercorn:
        hypercorn = {}

    ##    logs_path = Path(platformdirs.user_log_path(FILE_TITLE, __author__))
    ##    if not logs_path.exists():
    ##        logs_path.mkdir(parents=True)

    ##    print(f"Logs Path: {str(logs_path)!r}\n")

    try:
        # Hypercorn config setup
        config: dict[str, object] = {
            "accesslog": "-",
            ##"errorlog": logs_path / time.strftime("log_%Y_%m_%d.log"),
        }
        # Load things from user controlled toml file for hypercorn
        config.update(hypercorn)
        # Override a few particularly important details if set by user
        config.update(
            {
                "worker_class": "trio",
            },
        )
        # Make sure address is in bind

        if insecure_bind_port is not None:
            raw_bound = config.get("insecure_bind", [])
            if not isinstance(raw_bound, Iterable):
                raise ValueError(
                    "main.bind must be an iterable object (set in config file)!",
                )
            bound = set(raw_bound)
            bound |= {f"{ip_addr}:{insecure_bind_port}"}
            config["insecure_bind"] = bound

            # If no secure port, use bind instead
            if secure_bind_port is None:
                config["bind"] = config["insecure_bind"]
                config["insecure_bind"] = []

            insecure_locations = combine_end(
                f"http://{addr}" for addr in sorted(bound)
            )
            print(f"Serving on {insecure_locations} insecurely")

        if secure_bind_port is not None:
            raw_bound = config.get("bind", [])
            if not isinstance(raw_bound, Iterable):
                raise ValueError(
                    "main.bind must be an iterable object (set in config file)!",
                )
            bound = set(raw_bound)
            bound |= {f"{ip_addr}:{secure_bind_port}"}
            config["bind"] = bound

            secure_locations = combine_end(
                f"https://{addr}" for addr in sorted(bound)
            )
            print(f"Serving on {secure_locations} securely")

        app.config["EXPLAIN_TEMPLATE_LOADING"] = False
        app.config["QUART_AUTH_DURATION"] = 24 * 60 * 60  # 1 day

        # We want pretty html, no jank
        app.jinja_options = {
            "trim_blocks": True,
            "lstrip_blocks": True,
        }

        app.add_url_rule("/<path:filename>", "static", app.send_static_file)
        app.secret_key = PEPPER

        config_obj = Config.from_mapping(config)

        print("(CTRL + C to quit)")

        trio.run(
            async_run_server,
            partial(serve, app, config_obj),
        )
    except BaseExceptionGroup as exc:
        caught = False
        for ex in exc.exceptions:
            if isinstance(ex, KeyboardInterrupt):
                print("Shutting down from keyboard interrupt")
                caught = True
                break
        if not caught:
            traceback.print_exception(exc)
            raise


DEFAULT_CONFIG_TOML: Final = """[main]
# Port server should run on.
# You might want to consider changing this to 80
port = 3004

# Port for SSL secured server to run on
#ssl_port = 443

# Helpful stack exchange website question on how to allow non root processes
# to bind to lower numbered ports
# https://superuser.com/questions/710253/allow-non-root-process-to-bind-to-port-80-and-443
# Answer I used: https://superuser.com/a/1482188/1879931

[hypercorn]
# See https://hypercorn.readthedocs.io/en/latest/how_to_guides/configuring.html#configuration-options
use_reloader = false
# SSL configuration details
#certfile = "/home/<your_username>/letsencrypt/config/live/<your_domain_name>.duckdns.org/fullchain.pem"
#keyfile = "/home/<your_username>/letsencrypt/config/live/<your_domain_name>.duckdns.org/privkey.pem"
"""


def run() -> None:
    """Run character simulator server."""
    parser = argparse.ArgumentParser(
        description="Webserver to help keep track of volunteer hours.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__title__} v{__version__}",
        help="Show the program version and exit.",
    )
    parser.add_argument(
        "--create-default-config",
        action="store_true",
        help="Create or overwrite the default configuration file.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Bind to localhost (127.0.0.1) instead of public ip address.",
    )

    args = parser.parse_args()

    main_config = Path(MAIN_CONFIG)
    if args.create_default_config:
        print(
            f"Creating/overwriting configuration file located at {str(MAIN_CONFIG)!r} with default...",
        )
        config_path = Path(CONFIG_PATH)
        if not config_path.exists():
            config_path.mkdir(parents=True)

        main_config.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")

        print("Action complete.")
        return

    if main_config.exists():
        print(f"Reading configuration file {str(MAIN_CONFIG)!r}...\n")

        with main_config.open("rb") as fp:
            config = tomllib.load(fp)
    else:
        print(
            f"Configuration file {str(main_config)!r} not found, loading default.",
        )
        config = tomllib.loads(DEFAULT_CONFIG_TOML)

    main_section = config.get("main", {})

    insecure_bind_port = main_section.get("port", None)
    secure_bind_port = main_section.get("ssl_port", None)

    hypercorn: dict[str, object] = config.get("hypercorn", {})

    ip_address: str | None = None
    if True:  # args.local:
        ip_address = "127.0.0.1"

    run_server(
        secure_bind_port=secure_bind_port,
        insecure_bind_port=insecure_bind_port,
        ip_addr=ip_address,
        hypercorn=hypercorn,
    )


if __name__ == "__main__":
    run()
