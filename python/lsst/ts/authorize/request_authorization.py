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

__all__ = ["request_authorization"]

import argparse
import asyncio

from lsst.ts import salobj

from .handler_utils import check_csc, check_user_host


def print_log_message(data: salobj.BaseMsgType) -> None:
    print(data.message)


async def request_authorization_impl() -> None:
    """Implementation of the request_authorization function."""
    parser = argparse.ArgumentParser(
        "Request authorization changes for one or more CSCs."
    )
    parser.add_argument("cscs", nargs="+", help="CSCs to change")
    parser.add_argument(
        "-u",
        "--auth-users",
        nargs="*",
        help="List of user@host to authorize; " "'me' is replaced with your user@host.",
    )
    parser.add_argument(
        "-c",
        "--nonauth-cscs",
        nargs="*",
        help="CSCs to block,in the form 'name:index' for indexed CSCs "
        "and 'name' for non-indexed CSCs. ",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-a",
        "--add",
        action="store_true",
        help="Add these entries (authorize the users and de-authorize the CSCs).",
    )
    group.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="Remove these entries (de-authorize the users and authorize the CSCs).",
    )
    args = parser.parse_args()
    me = salobj.get_user_host()

    if args.add:
        prefix = "+ "
    elif args.remove:
        prefix = "- "
    else:
        prefix = ""

    def replace_me(user_host: str) -> str:
        """Replace "me" with the value of ``me``."""
        if user_host == "me":
            return me
        return user_host

    try:
        cscs_to_command_list = [check_csc(csc) for csc in args.cscs]
        cscs_to_command_str = ", ".join(cscs_to_command_list)

        if args.auth_users is None:
            auth_users_str = ""
        else:
            auth_users_list = [
                check_user_host(replace_me(user_host)) for user_host in args.auth_users
            ]
            auth_users_str = prefix + ", ".join(auth_users_list)

        if args.nonauth_cscs is None:
            nonauth_cscs_str = ""
        else:
            nonauth_cscs_list = [check_csc(csc) for csc in args.nonauth_cscs]
            nonauth_cscs_str = prefix + ", ".join(nonauth_cscs_list)
    except ValueError as e:
        parser.error(str(e))

    print(f"CSCs to change: {cscs_to_command_str!r}")
    print(f"Authorized users: {auth_users_str!r}")
    print(f"Non-authorized CSCs: {nonauth_cscs_str!r}")

    async with salobj.Domain() as domain, salobj.Remote(
        domain=domain, name="Authorize", index=None
    ) as remote:
        remote.evt_logMessage.callback = print_log_message

        await remote.cmd_requestAuthorization.set_start(
            cscsToChange=cscs_to_command_str,
            authorizedUsers=auth_users_str,
            nonAuthorizedCSCs=nonauth_cscs_str,
        )


def request_authorization() -> None:
    """Request authorization."""
    asyncio.run(request_authorization_impl())
