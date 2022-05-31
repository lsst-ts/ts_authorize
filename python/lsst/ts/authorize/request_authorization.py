__all__ = ["request_authorization"]

import argparse
import asyncio

from .utils import check_csc, check_user_host
from lsst.ts import salobj


def print_log_message(data):
    print(data.message)


async def request_authorization_impl():
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

    def replace_me(user_host):
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


def request_authorization():
    """Request authorization."""
    asyncio.run(request_authorization_impl())
