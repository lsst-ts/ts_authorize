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

import re
from dataclasses import dataclass
from enum import Enum

from lsst.ts import salobj

__all__ = [
    "AuthRequestData",
    "ExecutionStatus",
    "check_cscs",
    "check_user_host",
    "create_failed_error_message",
]

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


def check_cscs(cscs: set[str]) -> set[str]:
    """Check one of more csc name[:index] values.

    Returns
    -------
    cscs : `set` of `str`
        The ``cscs`` values argument, if valid.

    Raises
    ------
    ValueError
        If at least one value in ``cscs`` is not valid.
    """
    for csc in cscs:
        if not CSC_NAME_INDEX_RE.match(csc):
            raise ValueError(f"Invalid CSC[:index]: {csc!r}")
    return cscs


# TODO DM-36097: Change to checking a list of user/host names instead of one
#  at a time.
def check_user_host(user_host: str) -> str:
    """Check a user@host value.

    Returns
    -------
    user_host : str
        The ``user_host`` argument, if valid.

    Raises
    ------
    ValueError
        If ``user_host`` is not valid.
    """
    if USER_HOST_RE.match(user_host):
        return user_host
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
