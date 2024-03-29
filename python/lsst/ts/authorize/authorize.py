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
from .handler import AutoAuthorizeHandler, BaseAuthorizeHandler, RestAuthorizeHandler
from .handler_utils import AuthRequestData


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

        # Configuration items.
        self.config: None | types.SimpleNamespace = None
        self.poll_interval: int = 1
        self.timeout_request_authorization: int = 1

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
        self.poll_interval = config.poll_interval
        self.timeout_request_authorization = config.timeout_request_authorization

        if self.config.auto_authorization:
            self.log.info("Enabling auto authorization.")
            self.authorize_handler = AutoAuthorizeHandler(
                domain=self.salinfo.domain, log=self.log
            )
        else:
            self.log.info("Enabling REST authorization.")
            self.authorize_handler = RestAuthorizeHandler(
                domain=self.salinfo.domain,
                log=self.log,
                config=self.config,
                callback=self.error_callback,
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
        self.assert_enabled()

        await self.cmd_requestAuthorization.ack_in_progress(
            data, timeout=self.timeout_request_authorization
        )

        auth_request_data = AuthRequestData.from_auth_data(data)
        await self.authorize_handler.handle_authorize_request(data=auth_request_data)

    async def handle_summary_state(self) -> None:
        if self.summary_state == salobj.State.ENABLED:
            self.log.info("Starting authorize handler.")
            assert self.authorize_handler is not None
            await self.authorize_handler.start(self.poll_interval)
        else:
            if self.authorize_handler is not None:
                self.log.info("Stopping authorize handler.")
                await self.authorize_handler.stop()

    async def error_callback(self, code: int, report: str) -> None:
        """Callback coroutine for error handling of the authorize handler.

        Parameters
        ----------
        code : `int`
            The error code.
        report : `str`
            The error report.
        """
        await self.fault(code=code, report=report)


def run_authorize() -> None:
    asyncio.run(Authorize.amain(index=None))
