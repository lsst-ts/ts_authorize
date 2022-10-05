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

import types
import unittest

from aiohttp import web
from aiohttp.test_utils import TestServer
from auth_request_data import (
    APPROVED_AUTH_REQUESTS,
    APPROVED_PROCESSED_AUTH_REQUESTS,
    INDEX1,
    INDEX2,
    PENDING_AUTH_REQUESTS,
)
from lsst.ts import authorize, salobj


class RestAuthorizeHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        salobj.set_random_lsst_dds_partition_prefix()

        # SalObj Domain for the RestAuthorizeHandler.
        domain = salobj.Domain()
        # Configuration for the RestAuthorizeHandler.
        config = types.SimpleNamespace(
            host="localhost",
            port=5000,
        )
        self.handler = authorize.handler.RestAuthorizeHandler(
            domain=domain, config=config
        )

        # Setup the test REST server.
        app = web.Application()
        url_part = authorize.handler.AUTHLISTREQUEST_API
        app.router.add_get(url_part, self.request_handler)
        app.router.add_post(authorize.handler.AUTHLISTREQUEST_API, self.request_handler)
        app.router.add_put(
            authorize.handler.AUTHLISTREQUEST_API + authorize.handler.ID_EXECUTE_PARAMS,
            self.put_request_handler,
        )
        self.server = TestServer(app=app, port=5000)
        await self.server.start_server()

        # The expected result. This adjusted to be set in the course of the
        # test case so the get_handler returns the expected response.
        self.expected_rest_message: authorize.handler.RestMessageTypeList = []

    async def request_handler(self, request: web.Request) -> web.Response:
        """General handler coroutine for the test REST server."""
        return web.json_response(self.expected_rest_message)

    async def put_request_handler(self, request: web.Request) -> web.Response:
        """PUT handler coroutine for the test REST server."""
        request_id = int(request.match_info["request_id"])
        response_dict = APPROVED_PROCESSED_AUTH_REQUESTS[request_id]
        return web.json_response(response_dict)

    async def asyncTearDown(self) -> None:
        await self.server.close()

    async def validate_auth_requests(
        self,
        response_list: authorize.handler.RestMessageTypeList,
        auth_request_list: authorize.handler.RestMessageTypeList,
    ) -> None:
        assert len(response_list) == len(auth_request_list)
        if len(response_list) > 0:
            for response, auth_request in zip(response_list, auth_request_list):
                assert response["cscs_to_change"] == auth_request["cscs_to_change"]
                assert response["authorized_users"] == auth_request["authorized_users"]
                assert (
                    response["unauthorized_cscs"] == auth_request["unauthorized_cscs"]
                )

    async def test_process_approved_and_unprocessed_auth_requests(self) -> None:
        async with authorize.MinimalTestCsc(
            index=INDEX1
        ) as csc1, authorize.MinimalTestCsc(index=INDEX2) as csc2:
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            for aar in APPROVED_AUTH_REQUESTS:
                self.expected_rest_message = aar.rest_messages
                await self.handler.process_approved_and_unprocessed_auth_requests()
                await self.validate_auth_requests(
                    response_list=self.handler.response,
                    auth_request_list=self.expected_rest_message,
                )

                assert csc1.salinfo.authorized_users == aar.expected_authorized_users[0]
                assert (
                    csc1.salinfo.non_authorized_cscs
                    == aar.expected_non_authorized_cscs[0]
                )
                assert csc2.salinfo.authorized_users == aar.expected_authorized_users[1]
                assert (
                    csc2.salinfo.non_authorized_cscs
                    == aar.expected_non_authorized_cscs[1]
                )
                assert (
                    self.handler.csc_failed_messages.keys() == aar.expected_failed_cscs
                )

    async def test_handle_authorize_request(self) -> None:
        for pending_auth_request in PENDING_AUTH_REQUESTS:
            self.expected_rest_message = pending_auth_request.rest_messages
            data = types.SimpleNamespace(
                authorizedUsers=pending_auth_request.rest_messages[0][
                    "authorized_users"
                ],
                cscsToChange=pending_auth_request.rest_messages[0]["cscs_to_change"],
                nonAuthorizedCSCs=pending_auth_request.rest_messages[0][
                    "unauthorized_cscs"
                ],
                private_identity="RestAuthorizeHandlerTestCase",
            )
            await self.handler.handle_authorize_request(data)
            await self.validate_auth_requests(
                response_list=self.handler.response,
                auth_request_list=self.expected_rest_message,
            )
