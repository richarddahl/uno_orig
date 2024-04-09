from __future__ import annotations
from typing import Any
import decimal
from datetime import datetime, timedelta, date

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from babel import dates, numbers  # type: ignore

from uno.errors import UnauthorizedError  # type: ignore
from config import settings  # type: ignore

string_hasher = PasswordHasher()


# Column Default functions
async def set_group_id(group_id: int) -> None:
    pass


async def set_owner_id(owner_id: int) -> None:
    pass


# User Functions
async def create_hash(string) -> str:
    """Transforms the string from its plaintext to a cryptographic hash"""
    return string_hasher.hash(string)


async def validate_hash(hashed_string, string) -> bool:
    """Validates that the string matches the hashed string"""
    try:
        return string_hasher.verify(hashed_string, string)
    except VerifyMismatchError:
        raise UnauthorizedError(401, detail="Invalid password")


# Mask functions
def boolean_to_string(boolean: bool) -> str:
    return "Yes" if boolean is True else "No"


def date_to_string(date: date | None) -> str | None:
    return dates.format_date(date, format="medium", locale="en_US") if date else None


def datetime_to_string(datetime: datetime | None) -> str | None:
    return (
        dates.format_datetime(datetime, format="medium", locale=settings.LOCALE)
        if datetime
        else None
    )


def decimal_to_string(dec: decimal.Decimal | None) -> str | None:
    return numbers.format_decimal(dec, locale="en_US") if dec else None


def obj_to_string(model: Any) -> str | None:
    return model.__str__() if model else None


def timedelta_to_string(time_delta: timedelta | None) -> str | None:
    return dates.format_timedelta(time_delta, locale="en_US") if time_delta else None


def boolean_to_okui(boolean: bool) -> dict[str, Any] | None:
    if boolean is None:
        return None
    return {
        "value": boolean,
        "type": "boolean",
        "element": "checkbox",
        "label": "FIGURE THIS OUT",
    }


def date_to_okui(date: date | None) -> str | None:
    return dates.format_date(date, format="medium", locale="en_US") if date else None


def datetime_to_okui(datetime: datetime | None) -> str | None:
    return (
        dates.format_datetime(datetime, format="medium", locale="en_US")
        if datetime
        else None
    )


def decimal_to_okui(dec: decimal.Decimal | None) -> dict[str, Any] | None:
    return {"value": dec, "type": "decimal", "element": "imput"} if dec else None


def obj_to_okui(model: Any) -> str | None:
    return model.__str__() if model else None


def timedelta_to_okui(time_delta: timedelta | None) -> str | None:
    return (
        dates.format_timedelta(time_delta, locale=settings.LOCALE)
        if time_delta
        else None
    )
