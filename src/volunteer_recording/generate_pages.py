#!/usr/bin/env python3

"""Generate pages for the volunteer recording web server.

Copyright (C) 2022-2026  CoolCat467

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

__title__ = "Generate Pages"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from volunteer_recording import htmlgen, server

if TYPE_CHECKING:
    from collections.abc import Callable

MODULE: Final = Path(__file__).absolute().parent
SOURCE_ROOT: Final = MODULE.parent.parent

TEMPLATE_FOLDER: Final = MODULE / "templates"
TEMPLATE_FUNCTIONS: dict[Path, Callable[[], str]] = {}
STATIC_FOLDER: Final = MODULE / "static"
STATIC_FUNCTIONS: dict[Path, Callable[[], str]] = {}


def save_content(path: Path, content: str) -> None:
    """Save content to given path."""
    path.write_text(content + "\n", encoding="utf-8")
    print(f"Saved content to {path}")


def save_template_as(
    filename: str,
) -> Callable[[Callable[[], str]], Callable[[], str]]:
    """Save generated template as filename."""
    path = TEMPLATE_FOLDER / f"{filename}.html.jinja"

    def function_wrapper(function: Callable[[], str]) -> Callable[[], str]:
        if path in TEMPLATE_FUNCTIONS:
            raise NameError(
                f"{filename!r} already exists as template filename",
            )
        TEMPLATE_FUNCTIONS[path] = function
        return function

    return function_wrapper


def save_static_as(
    filename: str,
) -> Callable[[Callable[[], str]], Callable[[], str]]:
    """Save generated static file as filename."""
    path = STATIC_FOLDER / filename

    def function_wrapper(function: Callable[[], str]) -> Callable[[], str]:
        if path in STATIC_FUNCTIONS:
            raise NameError(f"{filename!r} already exists as static filename")
        STATIC_FUNCTIONS[path] = function
        return function

    return function_wrapper


@save_static_as("style.css")
def generate_style_css() -> str:
    """Generate style.css static file."""
    mono = "SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace"
    return "\n".join(
        (
            htmlgen.css(
                ("*", "*::before", "*::after"),
                box_sizing="border-box",
                font_family="Lucida Console",
            ),
            htmlgen.css(("h1", "footer"), text_align="center"),
            htmlgen.css(("html", "body"), height="100%"),
            htmlgen.css(
                "body",
                line_height=1.5,
                _webkit_font_smoothing="antialiased",
                display="flex",
                flex_direction="column",
            ),
            htmlgen.css(".content", flex=(1, 0, "auto")),
            htmlgen.css(
                ".footer",
                flex_shrink=0,
            ),
            htmlgen.css(
                ("img", "picture", "video", "canvas", "svg"),
                display="block",
                max_width="100%",
            ),
            htmlgen.css(
                ("input", "button", "textarea", "select"),
                font="inherit",
            ),
            htmlgen.css(
                ("p", "h1", "h2", "h3", "h4", "h5", "h6"),
                overflow_wrap="break-word",
            ),
            htmlgen.css(
                ("#root", "#__next"),
                isolation="isolate",
            ),
            htmlgen.css(
                "code",
                padding=("0.2em", "0.4em"),
                background_color="rgba(158,167,179,0.4)",
                border_radius="6px",
                font_family=mono,
                line_height=1.5,
            ),
            htmlgen.css(
                "::placeholder",
                font_style="italic",
            ),
            htmlgen.css(
                ".box",
                background="ghostwhite",
                padding="0.5%",
                border_radius="4px",
                border=("2px", "solid", "black"),
                margin="0.5%",
                width="fit-content",
            ),
            htmlgen.css(
                ".center",
                text_align="center",
            ),
            htmlgen.css(
                "#noticeText",
                font_size="10px",
                display="inline-block",
                white_space="nowrap",
            ),
            htmlgen.css(
                (
                    'input[type="submit"]',
                    'button[type="submit"]',
                    ".submit_button",
                ),
                border=("1.5px", "solid", "black"),
                border_radius="4px",
                padding="0.5rem",
                margin_left="0.5rem",
                margin_right="0.5rem",
                min_width="min-content",
            ),
            htmlgen.css(
                (
                    "a.submit_button",
                    "a.submit_button:link",
                    "a.submit_button:visited",
                    "a.submit_button:hover",
                    "a.submit_button:active",
                ),
                text_decoration="none",
                color="inherit",
            ),
            htmlgen.css(
                ".user-table",
                border_collapse="collapse",
            ),
            htmlgen.css(
                (
                    ".user-table th",
                    ".user-table td",
                ),
                border=("1px", "solid", "black"),
                padding="8px",
                text_align="left",
            ),
            htmlgen.css(
                ".user-table th",
                background="#eee",
            ),
            htmlgen.css(
                ".user-table .submit_button",
                display="inline-block",
                margin=0,
            ),
            htmlgen.css(
                "@media (prefers-color-scheme: dark)",
                htmlgen.css(
                    "body",
                    background_color="#181818",
                    color="#e0e0e0",
                ),
                htmlgen.css(
                    "a",
                    color="#8ab4f8",
                ),
                htmlgen.css(
                    "a:visited",
                    color="#c58af9",
                ),
                htmlgen.css(
                    "a:hover",
                    color="#aecbfa",
                    text_decoration="underline",
                ),
                htmlgen.css(
                    "a:focus-visible",
                    outline="2px solid currentColor",
                    outline_offset="3px",
                ),
                htmlgen.css(
                    ".box",
                    background_color="#1e1e1e",
                    border=("2px", "solid", "#444"),
                ),
                htmlgen.css(
                    "code",
                    background_color="rgba(255, 255, 255, 0.1)",
                ),
                htmlgen.css(
                    ("input", "button"),
                    background_color="#1e1e1e",
                    color="#e0e0e0",
                    border=("2px", "solid", "#444"),
                ),
                htmlgen.css(
                    ("input:hover", "button:hover"),
                    background_color="#4a4a4a",
                ),
                htmlgen.css(
                    ".user-table th",
                    background="#333",
                    color="#f5f5f5",
                ),
            ),
        ),
    )


@save_template_as("base")
def base_template() -> str:
    """Generate base HTML Template for application."""
    head_data = "\n".join(
        (
            htmlgen.tag(
                "link",
                rel="stylesheet",
                type_="text/css",
                href="/style.css",
            ),
            htmlgen.jinja_block("head", scoped=True),
        ),
    )

    footer = f"{server.__title__} v{server.__version__} © {server.__author__}"

    body_data = "\n".join(
        (
            htmlgen.wrap_tag(
                "div",
                "\n".join(
                    (
                        htmlgen.wrap_tag(
                            "h1",
                            htmlgen.jinja_expression("self.title()"),
                            False,
                        ),
                        htmlgen.jinja_block(
                            "body",
                            scoped=True,
                            required=True,
                        ),
                    ),
                ),
                class_="content",
            ),
            htmlgen.wrap_tag(
                "footer",
                "\n".join(
                    (
                        htmlgen.wrap_tag(
                            "i",
                            "If you're reading this, the web server was installed correctly.™",
                            block=False,
                        ),
                        htmlgen.tag("hr"),
                        htmlgen.wrap_tag(
                            "p",
                            footer,
                            block=False,
                        ),
                    ),
                ),
            ),
        ),
    )

    return htmlgen.template(
        htmlgen.jinja_block(
            "title",
            scoped=True,
            required=True,
            block=False,
        ),
        body_data,
        head=head_data,
        lang=htmlgen.jinja_block(
            "lang",
            "en",
            scoped=True,
            block=False,
        ),
    )


def template(
    body: str | None = None,
    *,
    title: str | None = None,
    head: str | None = None,
    lang: str = "en",
    extends: str = "base",
) -> str:
    """Use base HTML Template for application."""
    sections = [
        htmlgen.jinja_extends(f"{extends}.html.jinja"),
    ]

    if title is not None:
        sections.append(
            htmlgen.jinja_block("title", title, block=False, scoped=True),
        )

    if head is not None:
        sections.append(htmlgen.jinja_block("head", head, scoped=True))

    if lang != "en":
        sections.append(
            htmlgen.jinja_block("lang", lang, scoped=True, block=False),
        )

    if body is not None:
        sections.append(htmlgen.jinja_block("body", body, scoped=True))

    return "\n".join(sections)


@save_template_as("error_page")
def generate_error_page() -> str:
    """Generate error response page."""
    error_text = htmlgen.wrap_tag("p", htmlgen.jinja_expression("error_body"))
    content = "\n".join(
        (
            error_text,
            htmlgen.tag("br"),
            htmlgen.jinja_if_block(
                {
                    "return_link": "\n".join(
                        (
                            htmlgen.create_link(
                                htmlgen.jinja_expression("return_link"),
                                "Return to previous page",
                            ),
                            htmlgen.tag("br"),
                        ),
                    ),
                },
            ),
            htmlgen.create_link("/", "Return to main page"),
        ),
    )
    body = htmlgen.contain_in_box(content)
    return template(
        body,
        title=htmlgen.jinja_expression("page_title"),
    )


@save_template_as("root")
def generate_root() -> str:
    """Generate / (root) GET page."""
    head = htmlgen.wrap_tag(
        "style",
        "\n".join(
            (
                htmlgen.css(
                    ".giga_button",
                    width="97vw",
                    min_height="50vh",
                    font_size="clamp(2rem,10vw,8rem)",
                    margin="0.5%",
                ),
                htmlgen.css(
                    ".text_right",
                    text_align="right",
                ),
            ),
        ),
    )

    html = "<br>\n".join(
        (
            htmlgen.create_link(
                "/check-in",
                htmlgen.wrap_tag(
                    "button",
                    "Check-in",
                    block=False,
                    class_="giga_button submit_button",
                ),
            ),
            htmlgen.create_link(
                "/check-out",
                htmlgen.wrap_tag(
                    "button",
                    "Check-out",
                    block=False,
                    class_="giga_button submit_button center",
                ),
            ),
            htmlgen.wrap_tag(
                "div",
                htmlgen.create_link(
                    "/admin-login",
                    "Administration login",
                ),
                class_="text_right",
            ),
        ),
    )

    return template(html, title="Volunteer Recording", head=head)


@save_template_as("return_footer")
def return_footer_page() -> str:
    """Generate return footer page."""
    return_button = htmlgen.wrap_tag(
        "a",
        htmlgen.jinja_block(
            "return_text",
            "Return to main page",
            scoped=True,
            block=False,
        ),
        block=False,
        class_="submit_button",
        href=htmlgen.jinja_block(
            "return_link",
            "/",
            scoped=True,
            block=False,
        ),
    )

    return template(return_button)


def template_return_footer(
    body: str | None = None,
    *,
    title: str | None = None,
    head: str | None = None,
    lang: str = "en",
    return_text: str | None = None,
    return_link: str | None = None,
    extends: str = "return_footer",
) -> str:
    """Use admin signout footer HTML Template for application."""
    sections = [
        template(body, title=title, head=head, lang=lang, extends=extends),
    ]

    if return_text is not None:
        sections.append(
            htmlgen.jinja_block(
                "return_text",
                return_text,
                scoped=True,
                block=False,
            ),
        )

    if return_link is not None:
        sections.append(
            htmlgen.jinja_block(
                "return_link",
                return_link,
                scoped=True,
                block=False,
            ),
        )

    return "\n".join(sections)


@save_template_as("phone_input")
def generate_phone_input() -> str:
    """Generate phone digits input GET page."""
    head = htmlgen.wrap_tag(
        "style",
        "\n".join(
            (
                htmlgen.css(
                    (
                        ".giga_input",
                        'input[type="submit"]',
                    ),
                    width="50vw",
                    min_height="50vh",
                    font_size="clamp(2rem,10vw,8rem)",
                    margin="0.5%",
                    text_align="center",
                ),
                htmlgen.css(
                    "button",
                    display="block",
                ),
            ),
        ),
    )

    body = htmlgen.wrap_tag(
        "div",
        htmlgen.form(
            "phone_digits",
            htmlgen.input_field(
                "code",
                None,
                attrs={
                    "inputmode": "numeric",
                    "pattern": "[0-9]{4}",
                    "maxlength": "4",
                    "minlength": "4",
                    "min": 0,
                    "max": 9999,
                    "autocomplete": "off",
                    "required": True,
                    "autofocus": True,
                    "class": "giga_input",
                },
            ),
            "Submit",
        ),
        class_="center",
    )

    html = "\n".join(
        (
            body,
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
        ),
    )

    return template_return_footer(
        html,
        title="Enter the last 4 digits of your phone number",
        head=head,
    )


@save_template_as("select_user")
def generate_select_user_get() -> str:
    """Generate select user from list GET page."""
    return_link = htmlgen.jinja_expression("return_link")

    select_user_button = htmlgen.wrap_tag(
        "button",
        "Select",
        block=False,
        type_="submit",
        name="user_id",
        value=htmlgen.jinja_expression("user_id"),
    )

    user_list = htmlgen.jinja_table(
        None,
        ("First Name", "Last Name", "Select"),
        htmlgen.jinja_table_row(
            ("user_id", "user"),
            "user_records",
            "\n".join(
                (
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression("user.firstname|escape"),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression("user.lastname|escape"),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        select_user_button,
                        block=False,
                    ),
                ),
            ),
        ),
        class_="user-table center",
    )

    user_list_or_message = htmlgen.jinja_if_block(
        {
            "records_exist": user_list,
            "show_create": htmlgen.wrap_tag(
                "p",
                "No users currently exist with this code. Press the button below to create one.",
                block=False,
            ),
            "": htmlgen.wrap_tag(
                "p",
                "No users currently exist with this code.",
                block=False,
            ),
        },
    )

    back_link = htmlgen.wrap_tag(
        "a",
        "Enter a different code",
        block=False,
        class_="submit_button",
        href=return_link,
    )

    create_new_user_button = htmlgen.wrap_tag(
        "button",
        "Create new user",
        block=False,
        type_="submit",
        name="create_user",
    )

    create_new_user_section = htmlgen.jinja_if_block(
        {"show_create": create_new_user_button},
    )

    form_content = "\n".join(
        (
            user_list_or_message,
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
            back_link,
            create_new_user_section,
        ),
    )

    html = htmlgen.form("select_user", form_content)

    title_extra = htmlgen.jinja_if_block(
        {
            "show_create": " or create a new account",
        },
        block=False,
    )

    return template_return_footer(
        html,
        title=f"Select your user{title_extra}",
    )


@save_template_as("input_user_data")
def input_user_data_table() -> str:
    """Generate return footer page."""
    rows = (
        (
            htmlgen.input_field(
                "firstname",
                "First name",
                attrs={
                    "required": True,
                    "autocomplete": "off",
                    "minlength": 2,
                    "maxlength": 100,
                    "size": 30,
                    "value": htmlgen.jinja_expression(
                        "autofill_firstname|default('')",
                    ),
                },
            ),
            htmlgen.input_field(
                "lastname",
                "Last name",
                attrs={
                    "required": True,
                    "autocomplete": "off",
                    "minlength": 2,
                    "maxlength": 100,
                    "size": 30,
                    "value": htmlgen.jinja_expression(
                        "autofill_lastname|default('')",
                    ),
                },
            ),
        ),
        (
            htmlgen.input_field(
                "date_of_birth",
                "Date of birth",
                field_type="date",
                attrs={
                    "required": True,
                    "autocomplete": "off",
                    "minlength": 2,
                    "maxlength": 100,
                    "size": 30,
                    "value": htmlgen.jinja_expression(
                        "autofill_birthday|default('')",
                    ),
                },
            ),
            htmlgen.input_field(
                "code",
                "Last 4 digits of phone number",
                attrs={
                    "required": True,
                    "autocomplete": "off",
                    "inputmode": "numeric",
                    "pattern": "[0-9]{4}",
                    "maxlength": "4",
                    "minlength": "4",
                    "min": 0,
                    "max": 9999,
                    "size": 4,
                    "value": htmlgen.jinja_expression(
                        "autofill_code|default('')",
                    ),
                },
            ),
        ),
    )

    return htmlgen.render_table_rows(
        rows,
        first_is_header=False,
        cell_block=True,
    )


@save_template_as("create_user")
def generate_create_user_get() -> str:
    """Generate select user from list GET page."""
    return_link = htmlgen.jinja_expression("return_link")

    back_link = htmlgen.wrap_tag(
        "a",
        "Back to select user",
        block=False,
        class_="submit_button",
        href=return_link,
    )

    submit_button = htmlgen.wrap_tag(
        "button",
        "Create User",
        block=False,
        type_="submit",
    )

    input_fields_rows = htmlgen.jinja_include("input_user_data.html.jinja")

    form_content = "\n".join(
        (
            htmlgen.wrap_tag("table", input_fields_rows),
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
            back_link,
            submit_button,
        ),
    )

    html = htmlgen.form("create_user", form_content)

    return template_return_footer(
        html,
        title="Create a new account",
    )


@save_template_as("success")
def generate_success_page() -> str:
    """Generate success response page."""
    refreshes_after = htmlgen.jinja_expression("refreshes_after|default(10)")
    return_text = htmlgen.jinja_expression(
        "return_text|default('Return to main page')",
    )
    return_link = htmlgen.jinja_expression("return_link|default('/')")
    return_link_block = htmlgen.jinja_expression("self.return_link()")
    refresh_content = f"{refreshes_after};url={return_link_block}"

    custom_css = "\n".join(
        (
            htmlgen.css(
                ".success_check",
                display="block",
                color="#198754",
                font_size="5rem",
                line_height=1,
                margin=("1rem", "0"),
            ),
            htmlgen.css(
                ".box",
                border=("2px", "solid", "limegreen"),
            ),
        ),
    )

    head = "\n".join(
        (
            htmlgen.tag("meta", http_equiv="refresh", content=refresh_content),
            htmlgen.wrap_tag("style", custom_css),
        ),
    )

    refresh_time_plural = htmlgen.jinja_number_plural(
        "refreshes_after|default(10)",
        "second",
    )
    refresh_time_display = f"{refreshes_after} {refresh_time_plural}"

    message_content = htmlgen.wrap_tag(
        "p",
        htmlgen.jinja_expression("message"),
        block=False,
    )
    content = "\n".join(
        (
            message_content,
            htmlgen.wrap_tag(
                "span",
                "✓",
                block=False,
                class_="success_check center",
                aria_label="Success",
            ),
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
            htmlgen.tag("hr"),
            htmlgen.wrap_tag(
                "i",
                f"This page will automatically refresh after {refresh_time_display}.",
                block=False,
            ),
        ),
    )
    body = htmlgen.contain_in_box(content)
    return template_return_footer(
        body,
        title="Success",
        head=head,
        return_text=return_text,
        return_link=return_link,
    )


@save_template_as("prompt_password")
def generate_prompt_password_get() -> str:
    """Generate prompt password page."""
    error_message_content = htmlgen.wrap_tag(
        "i",
        htmlgen.jinja_expression("error_message"),
        block=False,
        style="".join(htmlgen.css_style(color="red"))[:-1],
    )

    error_message = htmlgen.jinja_if_block(
        {
            "error_message": error_message_content,
        },
    )

    back_link = htmlgen.wrap_tag(
        "a",
        "Back to select user",
        block=False,
        class_="submit_button",
        href="/admin-login",
    )

    submit_button = htmlgen.wrap_tag(
        "button",
        "Submit",
        block=False,
        type_="submit",
    )

    password_field_block = htmlgen.jinja_block(
        "password_field",
        htmlgen.input_field(
            "password",
            "Password",
            field_type="password",
            attrs={
                "required": True,
                "autofocus": True,
            },
        ),
        scoped=True,
    )

    contents = "\n".join(
        (
            password_field_block,
            htmlgen.tag("br"),
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
            back_link,
            submit_button,
        ),
    )

    body = "\n".join(
        (
            error_message,
            htmlgen.form(
                "password_prompt",
                contents,
            ),
        ),
    )

    return template_return_footer(
        body,
        title="Enter Password",
    )


def template_admin_signout_footer(
    body: str | None = None,
    *,
    title: str | None = None,
    head: str | None = None,
    lang: str = "en",
    sign_out_text: str = "Sign out",
    sign_out_link: str = "/admin/signout",
    extends: str = "return_footer",
) -> str:
    """Use admin signout footer HTML Template for application."""
    return template_return_footer(
        body,
        title=title,
        head=head,
        lang=lang,
        return_text=sign_out_text,
        return_link=sign_out_link,
        extends=extends,
    )


@save_template_as("admin_root")
def admin_root_get() -> str:
    """Generate admin root GET page."""
    link_list = htmlgen.contain_in_box(
        htmlgen.link_list(
            {
                "/admin/view-time-interval": "View time interval data",
                "/admin/edit-entries": "Edit Entries",
                "/admin/edit-categories": "Edit Categories",
                "/admin/edit-user": "Edit Users",
            },
        ),
        "Actions",
    )

    body = "\n".join(
        (
            link_list,
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
        ),
    )

    return template_admin_signout_footer(body, title="Administration Panel")


@save_template_as("admin_return_signout")
def admin_return_signout_page() -> str:
    """Generate admin return signout page."""
    return_root = htmlgen.wrap_tag(
        "a",
        htmlgen.jinja_block(
            "return_admin_panel_text",
            "Return to admin panel",
            scoped=True,
            block=False,
        ),
        block=False,
        class_="submit_button",
        href="/admin",
    )

    body = f"{htmlgen.jinja_super_block()}\n{return_root}"

    return template_admin_signout_footer(body)


def template_admin_return_signout_footer(
    body: str | None = None,
    *,
    title: str | None = None,
    head: str | None = None,
    lang: str = "en",
    sign_out_text: str = "Sign out",
    sign_out_link: str = "/admin/signout",
    return_admin_panel_text: str | None = None,
    extends: str = "admin_return_signout",
) -> str:
    """Use admin return signout footer HTML Template for application."""
    sections = [
        template_admin_signout_footer(
            body,
            title=title,
            head=head,
            lang=lang,
            sign_out_text=sign_out_text,
            sign_out_link=sign_out_link,
            extends=extends,
        ),
    ]

    if return_admin_panel_text is not None:
        sections.append(
            htmlgen.jinja_block(
                "return_admin_panel_text",
                return_admin_panel_text,
                scoped=True,
                block=False,
            ),
        )

    return "\n".join(sections)


@save_template_as("admin_select_edit_user")
def generate_admin_edit_user_get() -> str:
    """Generate admin select edit user from list GET page."""
    user_id = htmlgen.jinja_expression("user_id")

    select_user_button = htmlgen.wrap_tag(
        "a",
        "Edit",
        block=False,
        class_="submit_button",
        href=f"/admin/edit-user/{user_id}",
    )

    user_table = htmlgen.jinja_table(
        None,  # htmlgen.wrap_tag("h2", "User List", block=False),
        (
            "First Name",
            "Last Name",
            "Date of Birth",
            "Code",
            "Retired",
            "Admin",
            "Select",
        ),
        htmlgen.jinja_table_row(
            ("user_id", "user"),
            "user_records",
            "\n".join(
                (
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression("user.firstname|escape"),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression("user.lastname|escape"),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression(
                            "user.date_of_birth.isoformat()",
                        ),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_expression('"%04d"|format(user.code)'),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_checkbox(
                            "user.retired",
                            disabled=True,
                        ),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        htmlgen.jinja_checkbox(
                            "user.is_admin",
                            disabled=True,
                        ),
                        block=False,
                    ),
                    htmlgen.wrap_tag(
                        "td",
                        select_user_button,
                        block=False,
                    ),
                ),
            ),
        ),
        class_="user-table center",
    )

    html = "\n".join(
        (
            user_table,
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
        ),
    )

    return template_admin_return_signout_footer(
        html,
        title="Edit Users",
    )


@save_template_as("admin_edit_user")
def generate_admin_edit_user_modify_user_get() -> str:
    """Generate admin edit user GET page."""
    retired_checkbox = "\n".join(
        (
            htmlgen.wrap_tag(
                "label",
                "Retired",
                False,
                for_="retired_checkbox",
            ),
            htmlgen.jinja_checkbox(
                "autofill_retired|default(false)",
                jinja_properties=(
                    htmlgen.jinja_if_block(
                        {
                            "self_modification": 'disabled="true" ',
                        },
                        block=False,
                    ),
                ),
                id_="retired_checkbox",
                name="retired",
            ),
        ),
    )

    is_admin = htmlgen.wrap_tag(
        "code",
        htmlgen.jinja_expression("is_admin"),
        block=False,
    )

    toggle_admin_button = htmlgen.jinja_if_block(
        {
            "self_modification": htmlgen.wrap_tag(
                "p",
                "Changing your own privileges is forbidden.",
            ),
            "is_admin": htmlgen.wrap_tag(
                "button",
                "Revoke Administrator Privileges",
                block=False,
                type_="submit",
                name="toggle_admin",
            ),
            "": htmlgen.wrap_tag(
                "button",
                "Grant Administrator Privileges",
                block=False,
                type_="submit",
                name="toggle_admin",
                style="".join(
                    htmlgen.css_style(border=("2px", "solid", "red")),
                ).removesuffix(";"),
            ),
        },
    )

    self_modification_warning = htmlgen.jinja_if_block(
        {
            "self_modification": htmlgen.wrap_tag(
                "p",
                " ".join(
                    """Some options are forbidden from being changed for
the currently logged in user for system integrity purposes. Have another
administrator change them on your behalf.""".splitlines(),
                ),
                block=False,
            ),
        },
    )

    current_admin_status_message = htmlgen.wrap_tag(
        "p",
        f"Is Admin: {is_admin}",
        block=False,
    )

    row1_elements = (
        retired_checkbox,
        current_admin_status_message,
    )
    row2 = htmlgen.table_row(
        "\n".join(
            (
                htmlgen.table_cell("", block=False),
                htmlgen.table_cell(toggle_admin_button),
            ),
        ),
    )

    input_fields_rows = "\n".join(
        (
            htmlgen.jinja_include("input_user_data.html.jinja"),
            htmlgen.table_row_elements(
                row1_elements,
                cell_block=True,
            ),
            row2,
        ),
    )

    return_link = htmlgen.jinja_expression("return_link")

    back_link = htmlgen.wrap_tag(
        "a",
        "Return to user list without saving",
        block=False,
        class_="submit_button",
        href=return_link,
    )

    submit_button = htmlgen.wrap_tag(
        "button",
        "Save Changes",
        block=False,
        type_="submit",
    )

    form_content = "\n".join(
        (
            htmlgen.wrap_tag("table", input_fields_rows),
            htmlgen.tag("br"),
            htmlgen.jinja_super_block(),
            back_link,
            submit_button,
        ),
    )

    html = "\n".join(
        (
            self_modification_warning,
            htmlgen.form("modify_user", form_content),
        ),
    )

    return template_admin_return_signout_footer(
        html,
        title="Edit User",
        sign_out_text="Sign out without saving",
        return_admin_panel_text="Return to admin panel without saving",
    )


def matches_disk_files(new_files: dict[Path, str]) -> bool:
    """Return if all new file contents match old file contents.

    Copied from src/trio/_tools/gen_exports.py, dual licensed under
    MIT and APACHE2.
    """
    for path, new_source in new_files.items():
        if not path.exists():
            return False
        # Strip trailing newline `save_content` adds.
        old_source = path.read_text(encoding="utf-8")[:-1]
        if old_source != new_source:
            return False
    return True


def process(do_test: bool) -> int:
    """Generate all page templates and static files. Return exit code."""
    new_files: dict[Path, str] = {}
    for filename, function in TEMPLATE_FUNCTIONS.items():
        new_files[filename] = function()
    for filename, function in STATIC_FUNCTIONS.items():
        new_files[filename] = function()

    matches_disk = matches_disk_files(new_files)

    if do_test:
        if not matches_disk:
            print("Generated sources are outdated. Please regenerate.")
            return 1
    elif not matches_disk:
        for path, new_source in new_files.items():
            save_content(path, new_source)
        print("\nRegenerated sources successfully.")
        # With pre-commit integration, show that we edited files.
        return 1
    print("Generated sources are up to date.")
    return 0


def run() -> int:
    """Regenerate all generated files."""
    parser = argparse.ArgumentParser(
        description="Generate static and template files",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="test if code is still up to date",
    )
    parsed_args = parser.parse_args()

    # Double-check we found the right directory
    assert (SOURCE_ROOT / "LICENSE").exists()

    return process(do_test=parsed_args.test)


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    sys.exit(run())
