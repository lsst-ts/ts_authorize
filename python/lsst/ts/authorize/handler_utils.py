# This file is part of ts_authorize.
#
# Developed for Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
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

from __future__ import annotations

import collections
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from lsst.ts import salobj

__all__ = [
    "AuthRequestData",
    "ExecutionStatus",
    "HeadersType",
    "RestMessageType",
    "RequestMessageType",
    "check_cscs",
    "check_user_hosts",
    "create_failed_error_message",
    "set_from_comma_separated_string",
]

# Define data types for improved readability of the code.
RestMessageType = dict[str, int | float | str | dict[str, Any]]
RequestMessageType = dict[str, Any]
HeadersType = dict[str, str]

CSC_NAME_INDEX_RE = re.compile(r"^[a-zA-Z][_A-Za-z0-9]*(:\d+)?$")
USER_HOST_RE = re.compile(r"^[a-zA-Z][-._A-Za-z0-9]*@[a-zA-Z0-9][-._A-Za-z0-9]*$")


@dataclass
class AuthRequestData:
    """DataClass representing data for auth requests."""

    authorized_users: str
    cscs_to_change: str
    non_authorized_cscs: str
    private_identity: str

    @classmethod
    def from_auth_data(cls, data: salobj.type_hints.BaseMsgType) -> AuthRequestData:
        return cls(
            authorized_users=data.authorizedUsers,
            cscs_to_change=data.cscsToChange,
            non_authorized_cscs=data.nonAuthorizedCSCs,
            private_identity=data.private_identity,
        )


class ExecutionStatus(str, Enum):
    FAILED = "Failed"
    PENDING = "Pending"
    SUCCESSFUL = "Successful"


def check_cscs(cscs: collections.abc.Iterable) -> None:
    """Check one of more csc name[:index] values.

    Raises
    ------
    ValueError
        If at least one value in ``cscs`` is not valid.
    """
    for csc in cscs:
        if not CSC_NAME_INDEX_RE.match(csc):
            raise ValueError(f"Invalid CSC[:index]: {csc!r}")


def check_user_hosts(user_hosts: collections.abc.Iterable) -> None:
    """Check one or more user@host values.

    Raises
    ------
    ValueError
        If at least one value in ``user_hosts`` is not valid.
    """
    for user_host in user_hosts:
        if not USER_HOST_RE.match(user_host):
            raise ValueError(f"Invalid user@host: {user_host!r}")


def create_failed_error_message(
    csc_failed_messages: dict[str, str], cscs_succeeded: set[str]
) -> str:
    """Create a message string containing the failed messages and succeeded
    CSC names.

    Parameters
    ----------
    csc_failed_messages : `dict` of `str`
        The failed messages.
    cscs_succeeded : `set` of `str`
        The succeeded CSC names.

    Returns
    -------
    str
        The message string.
    """
    return (
        f"Failed to set authList for one or more CSCs: {csc_failed_messages}. "
        f"The following CSCs were successfully updated: {cscs_succeeded}."
    )


def set_from_comma_separated_string(string_to_split: str) -> set[str]:
    """Split a comma separated string into a set of the items in the string.

    Whitespace in the items in removed.

    Parameters
    ----------
    string_to_split : `str`
        The comma separated string to split.

    Returns
    -------
    `set` of `str`
        A set of the items that were separated by a comma.
    """
    return {val.strip() for val in string_to_split.split(",")}
