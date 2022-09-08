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

import asyncio
import types

from lsst.ts import salobj

from . import __version__
from .config_schema import CONFIG_SCHEMA
from .handler import AutoAuthorizeHandler, BaseAuthorizeHandler


# TODO DM-36097: The RestAuthorizeHandler needs to be integrated with the CSC.
#   This will require setting up a recurring task that retrieves the approved
#   and unprocessed authorize requests, sending any incoming authorize
#   requests to the REST server and sending statuses to the REST server of the
#   authorize requests that have been approved and for which the corresponding
#   CSCs have been sent cmd_setAuthList to.
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
        self,
        config_dir: None | str = None,
        initial_state: salobj.State = salobj.State.STANDBY,
        override: str = "",
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

        # Handler for the authorize request.
        self.authorize_handler: None | BaseAuthorizeHandler = None

        self.config: None | types.SimpleNamespace = None

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure CSC.

        Parameters
        ----------
        config : `types.SimpleNamespace`

        Raises
        ------
        NotImplementedError
            If `config.auto_authorization == False`.
        """
        self.config = config

        if self.config.auto_authorization:
            self.authorize_handler = AutoAuthorizeHandler(
                domain=self.salinfo.domain, log=self.log
            )
        else:
            raise NotImplementedError(
                "Running in non-automatic authorization not implement yet."
            )

    @staticmethod
    def get_config_pkg() -> str:
        return "ts_config_ocs"

    async def do_requestAuthorization(
        self, data: salobj.type_hints.BaseMsgType
    ) -> None:
        """Implement the requestAuthorization command.

        Parameters
        ----------
        data : ``cmd_requestAuthorization.DataType``
            Command data.
        """

        assert self.authorize_handler is not None
        assert self.config is not None

        self.assert_enabled()

        await self.cmd_requestAuthorization.ack_in_progress(
            data, timeout=self.config.timeout_request_authorization
        )

        await self.authorize_handler.handle_authorize_request(data=data)


def run_authorize() -> None:
    asyncio.run(Authorize.amain(index=None))
