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

__all__ = ["BaseAuthorizeHandler"]

import logging
import types
from abc import ABC, abstractmethod

from lsst.ts import salobj

from .. import utils

# Timeout for sending setAuthList command (seconds)
TIMEOUT_SET_AUTH_LIST = 5


class BaseAuthorizeHandler(ABC):
    def __init__(
        self,
        domain: salobj.Domain,
        log: logging.Logger = None,
        config: types.SimpleNamespace = None,
    ) -> None:
        if log is not None:
            self.log = log.getChild(type(self).__name__)
        else:
            self.log = logging.getLogger(type(self).__name__)
        self.domain = domain
        self.config = config
        # Hold the names, indices and error messages for the CSC for which
        # sending the autList command failed. This is mostly for unit tests but
        # it also helps to avoid returning a tuple of a dict and a set.
        self.csc_failed_messages: dict[str, str] = {}
        # Hold the names and indices of the CSC for which sending the authList
        # command succeeded. This is mostly for unit tests but it also helps to
        # avoid returning a tuple of a dict and a set.
        self.cscs_succeeded: set[str] = set()

    @abstractmethod
    async def handle_authorize_request(
        self, data: salobj.type_hints.BaseMsgType
    ) -> None:
        """Handle an authorize request.

        Parameters
        ----------
        data : `salobj.type_hints.BaseMsgType`
            The data containing the authorize request as described in the
            corresponding xml file in ts_xml.
        """
        raise NotImplementedError

    async def process_authorize_request(
        self, data: salobj.type_hints.BaseMsgType
    ) -> None:
        """Process an authorize request. Contact each CSC in the request and
        send the setAuthList command.

        Parameters
        ----------
        data : `salobj.type_hints.BaseMsgType`
            The data containing the authorize request as described in the
            corresponding xml file in ts_xml.

        Notes
        -----
        All CSCs that can be contacted get changed, even if one or more CSCs
        cannot be contacted.
        """
        cscs_to_command = await self.validate_request(data=data)

        # Reset these variables so they don't have a value left from previous
        # calls to this function.
        self.csc_failed_messages = {}
        self.cscs_succeeded = set()

        for csc_name_index in cscs_to_command:
            csc_name, csc_index = salobj.name_to_name_index(csc_name_index)
            try:
                async with salobj.Remote(
                    domain=self.domain,
                    name=csc_name,
                    index=csc_index,
                    include=[],
                ) as remote:
                    await remote.cmd_setAuthList.set_start(
                        authorizedUsers=data.authorizedUsers,
                        nonAuthorizedCSCs=data.nonAuthorizedCSCs,
                        timeout=TIMEOUT_SET_AUTH_LIST,
                    )
                    self.log.info(
                        f"Set authList for {csc_name_index} to {data.authorizedUsers}"
                    )
            except salobj.AckError as e:
                self.csc_failed_messages[csc_name_index] = e.args[0]
                self.log.warning(
                    f"Failed to set authList for {csc_name_index}: {e.args[0]}"
                )

        self.cscs_succeeded = cscs_to_command - self.csc_failed_messages.keys()

    async def validate_request(self, data: salobj.type_hints.BaseMsgType) -> set[str]:
        """Validate a requestAuthorization command by checking the input
        integrity.

        Parameters
        ----------
        data : ``cmd_requestAuthorization.DataType``
            Command data.

        Returns
        -------
        cscs_to_command : `set` of `str`
            List of strings with name:index of the CSCs to send setAuthList
            commands to.

        Raises
        ------
        salobj.ExpectedError
            If no csc is specified.
        """

        # Check values
        cscs_to_command = {val.strip() for val in data.cscsToChange.split(",")}
        if not cscs_to_command:
            raise salobj.ExpectedError(
                "No CSCs specified in cscsToChange; command has no effect."
            )

        for csc in cscs_to_command:
            utils.check_csc(csc)

        auth_users = data.authorizedUsers
        if auth_users:
            if auth_users[0] in ("+", "-"):
                auth_users = auth_users[1:]
            for user in auth_users.split(","):
                utils.check_user_host(user.strip())

        nonauth_cscs = data.nonAuthorizedCSCs
        if nonauth_cscs:
            if nonauth_cscs[0] in ("+", "-"):
                nonauth_cscs = nonauth_cscs[1:]
            for csc in nonauth_cscs.split(","):
                utils.check_csc(csc.strip())

        return cscs_to_command
