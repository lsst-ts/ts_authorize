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

__all__ = ["RestAuthorizeHandler"]

import asyncio
import logging
import types

import aiohttp
from lsst.ts import salobj

from .base_authorize_handler import BaseAuthorizeHandler


class RestAuthorizeHandler(BaseAuthorizeHandler):
    """Authorize handler that uses REST calls to communicate with a REST
    server.

    Forward any incoming authrization requests to the REST server so
    an operator can approve or deny the request. Periodically poll the REST
    server for approved but unprocessed authorization requests so the
    corresponding CSCs may be informed.

    Parameters
    ----------
    domain : `salobj.Domain`
        The DDS domain of the CSCs.
    log : `logging.Logger`
        Create a child Logger of the provided Logger, or a new Logger if None.
    config : `types.SimpleNamespace`
        The configuration to use. This is the same configuration as received by
        the Authorize CSC.

    Attributes
    ----------
    response : `list` of `dict`
        A unmarshalled JSON response from the REST server.
    rest_url : `str`
        The REST entry point constructed from the host and port as provided via
        the config.
    lock : `asyncio.Lock`
        A Lock to ensure that certain operations are performed atomically.
    """

    def __init__(
        self,
        domain: salobj.Domain,
        log: logging.Logger = None,
        config: types.SimpleNamespace = None,
    ) -> None:
        super().__init__(domain=domain, log=log, config=config)
        assert self.config is not None
        self.response: None | list[dict[str, int | float | str]] = None
        self.rest_url = (
            f"http://{self.config.host}:{self.config.port}/api/authlistrequest/"
        )
        # Lock to prevent concurrent execution of GET and POST.
        self.lock = asyncio.Lock()

    async def handle_authorize_request(
        self, data: salobj.type_hints.BaseMsgType
    ) -> None:
        # Set up data to send over JSON
        authorized_users = data.authorizedUsers
        cscs_to_change = data.cscsToChange
        non_authorized_cscs = data.nonAuthorizedCSCs
        requested_by = data.private_identity

        # Send a POST with the authorize request data. The reply received from
        # the REST server is not used and is stored for testing purposes.
        async with self.lock, aiohttp.ClientSession() as session:
            async with session.get(
                self.rest_url,
                json={
                    "cscs_to_change": cscs_to_change,
                    "authorized_users": authorized_users,
                    "unauthorized_cscs": non_authorized_cscs,
                    "requested_by": requested_by,
                },
            ) as resp:
                self.response = await resp.json()

    async def get_approved_and_unprocessed_auth_requests(
        self,
    ) -> None:
        """GET the approved and unprocessed authorize requests from the REST
        server.

        These are authorize requests that have been approved by an
        operator and that have not been processed by this CSC yet.
        """
        async with self.lock, aiohttp.ClientSession() as session:
            async with session.get(self.rest_url) as resp:
                self.response = await resp.json()
                assert self.response is not None
                for response in self.response:
                    data = types.SimpleNamespace(
                        authorizedUsers=response["authorized_users"],
                        cscsToChange=response["cscs_to_change"],
                        nonAuthorizedCSCs=response["unauthorized_cscs"],
                    )
                    await self.process_authorize_request(data=data)

                    # TODO DM-36097: Add sending feedback to the REST server.
