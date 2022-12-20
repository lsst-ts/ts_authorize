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

__all__ = [
    "RestAuthorizeHandler",
    "RestMessageType",
    "AUTHLISTREQUEST_ENDPOINT",
    "GET_TOKEN_ENDPOINT",
    "ID_EXECUTE_PARAMS",
]

import asyncio
import logging
import os
import types
from http import HTTPStatus
from typing import Any

import aiohttp
from lsst.ts import salobj

from ..handler_utils import AuthRequestData, ExecutionStatus
from .base_authorize_handler import BaseAuthorizeHandler

# Define data types for improved readability of the code.
RestMessageType = dict[str, int | float | str | dict[str, Any]]
RequestMessageType = dict[str, Any]
HeadersType = dict[str, str]


AUTHLISTREQUEST_ENDPOINT = "/manager/api/authlistrequest/"
AUTHORIZED_PENDING_PARAMS = (
    f"?status=Authorized&execution_status={ExecutionStatus.PENDING}"
)
GET_TOKEN_ENDPOINT = "/manager/api/get-token/"
ID_EXECUTE_PARAMS = "{request_id}/execute"


class RestAuthorizeHandler(BaseAuthorizeHandler):
    """Authorize handler that uses REST calls to communicate with a REST
    server.

    Forward any incoming authorization requests to the REST server so
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
    authlistrequest_url : `str`
        The Auth List Request REST endpoint constructed from the host and port
        as provided via the config.
    get_token_url : `str`
        The Get Token REST endpoint constructed from the host and port as
        provided via the config.
    token : `str`
        The authentication token to put in the request headers.
    lock : `asyncio.Lock`
        A Lock to ensure that certain operations are performed atomically.
    """

    def __init__(
        self,
        domain: salobj.Domain,
        log: logging.Logger | None = None,
        config: types.SimpleNamespace | None = None,
    ) -> None:
        super().__init__(domain=domain, log=log, config=config)
        assert self.config is not None
        self.response: None | RestMessageType | list[RestMessageType] = None
        self.authlistrequest_url = (
            f"http://{self.config.host}:{self.config.port}" + AUTHLISTREQUEST_ENDPOINT
        )
        self.get_token_url = (
            f"http://{self.config.host}:{self.config.port}" + GET_TOKEN_ENDPOINT
        )
        self.token = ""
        # Lock to prevent concurrent execution of GET and POST.
        self.lock = asyncio.Lock()
        self.username = os.getenv("AUTHLIST_USER_NAME")
        self.password = os.getenv("AUTHLIST_USER_PASS")
        if self.username is None or self.password is None:
            raise RuntimeError(
                "Please set AUTHLIST_USER_NAME and AUTHLIST_USER_PASS environment variables."
            )

    async def _get_post_response(
        self, url: str, json: RequestMessageType, headers: HeadersType
    ) -> RestMessageType | list[RestMessageType]:
        async with self.lock, aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url=url, json=json) as resp:
                if resp.status == HTTPStatus.OK:
                    return await resp.json()
                else:
                    resp_json = await resp.json()
                    raise RuntimeError(
                        f"Got HTTP response status {resp.status} == {HTTPStatus(resp.status).name} "
                        f"and {resp_json=!s}."
                    )

    async def authenticate(self) -> None:
        """Authenticate against the REST server.

        Raises
        ------
        `RuntimeError`
            In case of an unexpected response.
        """
        json = {"username": self.username, "password": self.password}
        self.response = await self._get_post_response(
            url=self.get_token_url, json=json, headers={}
        )
        assert isinstance(self.response, dict)  # keep MyPy happy.
        if "data" in self.response.keys():
            assert isinstance(self.response["data"], dict)  # keep MyPy happy.
            self.token = self.response["data"]["token"]
        else:
            self.token = ""
            raise RuntimeError(f"Got unexpected response {self.response}.")

    async def handle_authorize_request(self, data: AuthRequestData) -> None:
        """Send a POST with the authorize request data.

        The reply received from the REST server is not used and is stored for
        testing purposes.

        Parameters
        ----------
        data : `AuthRequestData`
            The auth request data.
        """
        await self.authenticate()
        json = {
            "cscs_to_change": data.cscs_to_change,
            "authorized_users": data.authorized_users,
            "unauthorized_cscs": data.non_authorized_cscs,
            "requested_by": data.private_identity,
        }
        headers = {"Authorization": self.token}
        self.response = await self._get_post_response(
            url=self.authlistrequest_url, json=json, headers=headers
        )

    async def process_approved_and_unprocessed_auth_requests(self) -> None:
        """GET the approved and unprocessed authorize requests from the REST
        server and process them.

        These are authorize requests that have been approved by an
        operator and that have not been processed by this CSC yet.
        """
        await self.authenticate()
        async with self.lock, aiohttp.ClientSession(
            headers={"Authorization": self.token}
        ) as session:
            async with session.get(
                self.authlistrequest_url + AUTHORIZED_PENDING_PARAMS
            ) as resp:
                self.response = await resp.json()
                if self.response is not None:
                    for response in self.response:
                        assert isinstance(response, dict)  # keep MyPy happy.
                        data = AuthRequestData(
                            authorized_users=str(response["authorized_users"]),
                            cscs_to_change=str(response["cscs_to_change"]),
                            non_authorized_cscs=str(response["unauthorized_cscs"]),
                            private_identity=str(response["requested_by"]),
                        )
                        (
                            csc_failed_messages,
                            cscs_succeeded,
                        ) = await self.process_authorize_request(data=data)

                        response_id = response["id"]
                        execution_status = ExecutionStatus.SUCCESSFUL
                        execution_message = (
                            "The following CSCs were updated correctly: "
                            + ", ".join(sorted(cscs_succeeded))
                            + "."
                        )
                        if len(csc_failed_messages) > 0:
                            execution_status = ExecutionStatus.FAILED
                            failed_message = (
                                " The following CSCs failed to update correctly: "
                                + ", ".join(sorted(csc_failed_messages.keys()))
                                + "."
                            )
                            execution_message = execution_message + failed_message
                        put_path = ID_EXECUTE_PARAMS.format(request_id=response_id)
                        async with session.put(
                            self.authlistrequest_url + put_path,
                            json={
                                "execution_status": execution_status,
                                "execution_message": execution_message,
                            },
                        ) as put_resp:
                            put_resp_json = await put_resp.json()
                            put_resp_id = put_resp_json["id"]
                            put_resp_exec_stat = put_resp_json["execution_status"]
                            put_resp_exec_msg = put_resp_json["execution_message"]
                            if put_resp_id != response_id:
                                self.log.error(
                                    f"Response id = {put_resp_id} != request id = {response_id}"
                                )
                            else:
                                if put_resp_exec_stat != execution_status:
                                    self.log.error(
                                        f"Response id = {put_resp_id} == request id = {response_id} "
                                        f"but response execution status = {put_resp_exec_stat} != "
                                        f"request execution status {execution_status}"
                                    )
                                if put_resp_exec_msg != execution_message:
                                    self.log.error(
                                        f"Response id = {put_resp_id} == request id = {response_id} "
                                        f"but response execution message = {put_resp_exec_msg} != "
                                        f"request execution message {execution_message}"
                                    )

    async def start(self, sleep_time: float) -> None:
        # Make sure the task is not already running.
        self.periodic_task.cancel()
        # Now start the task.
        self.periodic_task = asyncio.create_task(self.perform_periodic_task(sleep_time))

    async def stop(self) -> None:
        self.periodic_task.cancel()

    async def perform_periodic_task(self, sleep_time: float) -> None:
        while True:
            await self.process_approved_and_unprocessed_auth_requests()
            await asyncio.sleep(sleep_time)
