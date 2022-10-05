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

__all__ = ["check_csc", "check_user_host"]

import re

CSC_NAME_INDEX_RE = re.compile(r"^[a-zA-Z][_A-Za-z0-9]*(:\d+)?$")
USER_HOST_RE = re.compile(r"^[a-zA-Z][-._A-Za-z0-9]*@[a-zA-Z0-9][-._A-Za-z0-9]*$")


# TODO DM-36097: Check against a list of known CSCs and change to checking a
#  list of CSC names instead of one at a time.
def check_csc(csc: str) -> str:
    """Check a csc name[:index] value.

    Returns
    -------
    csc : str
        The ``csc`` argument, if valid.

    Raises
    ------
    ValueError
        If ``csc`` is not valid.
    """
    if CSC_NAME_INDEX_RE.match(csc):
        return csc
    raise ValueError(f"Invalid CSC[:index]: {csc!r}")


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
