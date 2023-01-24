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

import asyncio
import logging
import os
import types
from collections.abc import Iterable
from http import HTTPStatus
from types import TracebackType
from typing import Type

import aiohttp
from lsst.ts import salobj

from ..handler_utils import AuthRequestData, ExecutionStatus, RestMessageType
from .base_authorize_handler import BaseAuthorizeHandler

__all__ = [
    "RestAuthorizeHandler",
    "RestMessageType",
    "AUTHLISTREQUEST_ENDPOINT",
    "GET_TOKEN_ENDPOINT",
    "ID_EXECUTE_PARAMS",
]

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
        self.response: None | RestMessageType | Iterable[RestMessageType] = None
        self.authlistrequest_url = (
            f"http://{self.config.host}:{self.config.port}" + AUTHLISTREQUEST_ENDPOINT
        )
        self.get_token_url = (
            f"http://{self.config.host}:{self.config.port}" + GET_TOKEN_ENDPOINT
        )
        self.token = ""
        self._client_session: aiohttp.ClientSession | None = None
        # Lock to prevent concurrent execution of GET and POST.
        self.lock = asyncio.Lock()
        self.username = os.getenv("AUTHLIST_USER_NAME")
        self.password = os.getenv("AUTHLIST_USER_PASS")
        if self.username is None or self.password is None:
            raise RuntimeError(
                "Please set AUTHLIST_USER_NAME and AUTHLIST_USER_PASS environment variables."
            )

    async def _get_response(
        self, resp: aiohttp.ClientResponse
    ) -> RestMessageType | Iterable[RestMessageType]:
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
        assert self.config is not None
        self.log.debug(f"Authenticating against host {self.config.host}.")
        json = {"username": self.username, "password": self.password}
        async with self.lock, self.client_session.post(
            url=self.get_token_url, json=json
        ) as resp:
            self.response = await self._get_response(resp=resp)
            assert isinstance(self.response, dict)  # keep MyPy happy.
            if "token" in self.response.keys():
                assert isinstance(self.response["token"], str)  # keep MyPy happy.
                self.token = self.response["token"]
                self.log.debug("Authentication successful.")
            else:
                self.token = ""
                self.log.error("Authentication unsuccessful.")
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
        self.log.debug("handle_authorize_request")
        await self.authenticate()
        json = {
            "cscs_to_change": data.cscs_to_change,
            "authorized_users": data.authorized_users,
            "unauthorized_cscs": data.non_authorized_cscs,
            "requested_by": data.private_identity,
        }
        async with self.lock, self.client_session.post(
            url=self.authlistrequest_url,
            json=json,
            headers={"Authorization": self.token},
        ) as resp:
            self.response = await self._get_response(resp=resp)

    async def process_approved_and_unprocessed_auth_requests(self) -> None:
        """GET the approved and unprocessed authorize requests from the REST
        server and process them.

        These are authorize requests that have been approved by an
        operator and that have not been processed by this CSC yet.
        """
        self.log.debug("process_approved_and_unprocessed_auth_requests")
        await self.authenticate()
        async with self.lock, self.client_session.get(
            self.authlistrequest_url + AUTHORIZED_PENDING_PARAMS,
            headers={"Authorization": self.token},
        ) as resp:
            self.response = await self._get_response(resp=resp)
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
                    async with self.client_session.put(
                        self.authlistrequest_url + put_path,
                        json={
                            "execution_status": execution_status,
                            "execution_message": execution_message,
                        },
                        headers={"Authorization": self.token},
                    ) as put_resp:
                        put_resp_json = await self._get_response(resp=put_resp)
                        assert isinstance(put_resp_json, dict)  # keep MyPy happy.
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

    async def perform_periodic_task(self, sleep_time: float) -> None:
        while True:
            await self.process_approved_and_unprocessed_auth_requests()
            await asyncio.sleep(sleep_time)

    @property
    def client_session(self) -> aiohttp.ClientSession:
        assert self._client_session is not None
        return self._client_session

    async def create_client_session(self) -> None:
        self.log.debug("create_client_session")
        if not self._client_session or self._client_session.closed:
            self._client_session = aiohttp.ClientSession()

    async def close_client_session(self) -> None:
        self.log.debug("close_client_session")
        if self._client_session and not self._client_session.closed:
            await self._client_session.close()

    async def start(self, sleep_time: float) -> None:
        self.log.debug("start")
        await self.create_client_session()
        # Make sure the task is not already running.
        self.periodic_task.cancel()
        # Now start the task.
        self.periodic_task = asyncio.create_task(self.perform_periodic_task(sleep_time))

    async def stop(self) -> None:
        self.log.debug("stop")
        self.periodic_task.cancel()
        await self.close_client_session()

    def __enter__(self) -> None:
        # This class only implements an async context manager.
        raise NotImplementedError("Use 'async with' instead.")

    def __exit__(
        self, type: Type[BaseException], value: BaseException, traceback: TracebackType
    ) -> None:
        # __exit__ should exist in pair with __enter__ but never be executed.
        raise NotImplementedError("Use 'async with' instead.")

    async def __aenter__(self) -> RestAuthorizeHandler:
        await self.create_client_session()
        return self

    async def __aexit__(
        self, type: Type[BaseException], value: BaseException, traceback: TracebackType
    ) -> None:
        await self.close_client_session()
