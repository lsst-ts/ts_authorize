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

from lsst.ts import salobj

from . import __version__
from . import utils
from .config_schema import CONFIG_SCHEMA

# Timeout for sending setAuthList command (seconds)
TIMEOUT_SET_AUTH_LIST = 5


class Authorize(salobj.ConfigurableCsc):
    """Manage authorization requests.

    The CSC receives requests for authorization from users and sets the
    authList on the required CSCs.

    A future update will allow the CSC to interact with LOVE to validate a user
    request before setting the authList. It will also receive requests from
    LOVE to set the authList.

    Parameters
    ----------
    config_dir : `str` (optional)
        Configuration directory.
    initial_state : `salobj.State` (optional)
        Initial state of the CSC.
    simulation_mode : `int` (optional)
        Initial simulation mode.
    components_to_handle : `set` or `str` (optional)
        Name of the components to handle authorization for. By default, handle
        all components with available IDL files.
    """

    valid_simulation_modes = (0,)
    version = __version__
    enable_cmdline_state = True

    def __init__(
        self, config_dir=None, initial_state=salobj.State.STANDBY, override=""
    ) -> None:
        super().__init__(
            name="Authorize",
            index=0,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=initial_state,
            override=override,
        )

        # Make sure the requestAuthorization command does not require
        # authorization.
        self.cmd_requestAuthorization.authorize = False

        self.config = None

    async def configure(self, config) -> None:
        """Configure CSC.

        Parameters
        ----------
        config : `types.SimpleNamespace`

        Raises
        ------
        NotImplementedError
            If `config.auto_authorization == False`.
        """

        # TODO: Implement validation with LOVE system.
        if not config.auto_authorization:
            raise NotImplementedError(
                "Running in non-automatic authorization not implement yet."
            )

        self.config = config

    @staticmethod
    def get_config_pkg():
        return "ts_config_ocs"

    async def do_requestAuthorization(self, data):
        """Implement the requestAuthorization command.

        Parameters
        ----------
        data : ``cmd_requestAuthorization.DataType``
            Command data.
        """

        self.assert_enabled()

        await self.cmd_requestAuthorization.ack_in_progress(
            data, timeout=self.config.timeout_request_authorization
        )

        cscs_to_command = await self.validate_request(data=data)

        cscs_failed_to_set_auth_list = set()
        for csc_name_index in cscs_to_command:
            csc_name, csc_index = salobj.name_to_name_index(csc_name_index)
            try:
                async with salobj.Remote(
                    domain=self.salinfo.domain,
                    name=csc_name,
                    index=csc_index,
                    include=[],
                ) as remote:
                    await remote.cmd_setAuthList.set_start(
                        authorizedUsers=data.authorizedUsers,
                        nonAuthorizedCSCs=data.nonAuthorizedCSCs,
                        timeout=TIMEOUT_SET_AUTH_LIST,
                    )
                self.log.info(f"Set authList for {csc_name_index}")
            except salobj.AckError as e:
                cscs_failed_to_set_auth_list.update({csc_name_index})
                self.log.warning(
                    f"Failed to set authList for {csc_name_index}: {e.args[0]}"
                )

        if len(cscs_failed_to_set_auth_list) > 0:
            raise RuntimeError(
                f"Failed to set authList for the following CSCs: {cscs_failed_to_set_auth_list}. "
                "The following CSCs were successfully updated: "
                f"{cscs_to_command-cscs_failed_to_set_auth_list}"
            )

    async def validate_request(self, data):
        """Validate a requestAuthorization command by checking the input
        integrity and authenticating the request with LOVE.

        Parameters
        ----------
        data : ``cmd_requestAuthorization.DataType``
            Command data.

        Returns
        -------
        cscs_to_command : `list` of `str`
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
