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
from lsst.ts.idl import get_idl_dir

__all__ = [
    "AuthRequestData",
    "ExecutionStatus",
    "RestMessageType",
    "check_cscs",
    "check_user_hosts",
    "create_failed_error_message",
    "set_from_comma_separated_string",
]

# Define data types for improved readability of the code.
RestMessageType = dict[str, int | float | str | dict[str, Any]]

CSC_NAME_INDEX_RE = re.compile(r"^[a-zA-Z][_A-Za-z0-9]*(:\d+)?$")
USER_HOST_RE = re.compile(r"^[a-zA-Z][-._A-Za-z0-9]*@[a-zA-Z0-9][-._A-Za-z0-9]*$")

# TODO DM-38683: Use lsst.ts.xml instead.
IDL_FILE_PATTERN_MATCH = re.compile(r"(.*)sal_revCoded_(?P<component>.*).idl")


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


# TODO DM-38683: Use lsst.ts.xml instead.
def _get_all_components() -> list[str]:
    """Get the name of all components in the system.

    Returns
    -------
    list[str]
        Name of all components in the system.
    """
    idl_dir = get_idl_dir()

    components: list[str] = {
        IDL_FILE_PATTERN_MATCH.match(str(idl_file)).groupdict()["component"]  # type: ignore
        for idl_file in idl_dir.glob("*idl")
    }

    return components


all_components = _get_all_components()


def check_cscs(cscs: collections.abc.Iterable) -> None:
    """Check one of more csc name[:index] values.

    Raises
    ------
    ValueError
        If at least one value in ``cscs`` is not valid.
    """
    bad_cscs = set()
    for csc in cscs:
        csc_name, csc_index = salobj.name_to_name_index(csc)
        # TODO DM-38683: Use lsst.ts.xml instead.
        if not CSC_NAME_INDEX_RE.match(csc) or csc_name not in all_components:
            bad_cscs.add(csc)
    if bad_cscs:
        raise ValueError(f'Invalid CSC[:index]s:  {", ".join(bad_cscs)}')


def check_user_hosts(user_hosts: collections.abc.Iterable) -> None:
    """Check one or more user@host values.

    Raises
    ------
    ValueError
        If at least one value in ``user_hosts`` is not valid.
    """
    bad_users = {
        user_host for user_host in user_hosts if not USER_HOST_RE.match(user_host)
    }
    if bad_users:
        raise ValueError(f'Invalid user@hosts: {", ".join(bad_users)}')


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
    success_message = (
        f'The following CSCs were successfully updated: {", ".join(sorted(cscs_succeeded))}.'
        if len(cscs_succeeded) > 0
        else "No CSCs were successfully updated."
    )
    failed_message = (
        f'Failed to set authList for one or more CSCs: {", ".join(sorted(csc_failed_messages))}.'
        if len(csc_failed_messages) > 0
        else ""
    )
    space_or_not = " " if failed_message else ""
    return success_message + space_or_not + failed_message


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
