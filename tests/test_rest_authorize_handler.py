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
from lsst.ts import authorize, salobj

# Indices for the test CSCs.
INDEX1 = 5
INDEX2 = 52

# The users that will receive authorization.
AUTH_USERS1 = "+test1@localhost, test2@localhost"
AUTH_USERS2 = "+test3@localhost"

# TODO DM-36097: Add some tests for requests with a leading - and some with no
#  prefix. Add a test utility that provides a sequence of valid auth request
#  data, with the expected result (authorized users and non-authorized CSCs) on
#  success.
# The unauthorized CSCs.
UNAUTH_CSCS1 = "+TestCSC2, TestCSC3:1"
UNAUTH_CSCS2 = "+TestCSC3:1"

# TODO DM-36097: Use a dataclass.
# A list representing a single pending authorize request.
PENDING_AUTH_REQUEST: list[dict[str, int | float | str]] = [
    {
        "id": 0,
        "resolved_by": "operator1@localhost",
        "user": "team_leader1@localhost",
        "cscs_to_change": f"Test:{INDEX1}",
        "authorized_users": AUTH_USERS1,
        "unauthorized_cscs": UNAUTH_CSCS1,
        "requested_by": "team_leader1@localhost",
        "requested_at": "2022-09-01T11:00:00.000Z",
        "duration": 60,
        "message": "Test message.",
        "status": "Pending",
        "resolved_at": "2022-09-01T11:05:00.000Z",
    }
]

# A list representing two approved authorize requests.
APPROVED_AUTH_REQUESTS: list[dict[str, int | float | str]] = [
    {
        "id": 0,
        "resolved_by": "operator1@localhost",
        "user": "team_leader1@localhost",
        "cscs_to_change": f"Test:{INDEX1}",
        "authorized_users": AUTH_USERS1,
        "unauthorized_cscs": UNAUTH_CSCS1,
        "requested_by": "team_leader1@localhost",
        "requested_at": "2022-09-01T11:00:00.000Z",
        "duration": 60,
        "message": "Test message.",
        "status": "Approved",
        "resolved_at": "2022-09-01T11:05:00.000Z",
    },
    {
        "id": 1,
        "resolved_by": "operator2@localhost",
        "user": "team_leader1@localhost",
        "cscs_to_change": f"Test:{INDEX1},Test:{INDEX2}",
        "authorized_users": AUTH_USERS2,
        "unauthorized_cscs": UNAUTH_CSCS2,
        "requested_by": "team_leader1@localhost",
        "requested_at": "2022-09-01T11:10:00.000Z",
        "duration": 60,
        "message": "Test message.",
        "status": "Approved",
        "resolved_at": "2022-09-01T11:15:00.000Z",
    },
]


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
        app.router.add_get("/api/authlistrequest/", self.get_handler)
        self.server = TestServer(app=app, port=5000)
        await self.server.start_server()

        # The expected result. This adjusted to be set in the course of the
        # test case so the get_handler returns the expected response.
        self.expected_result = PENDING_AUTH_REQUEST

    async def get_handler(self, request: web.Request) -> web.Response:
        """Handler coroutine for the test REST server."""
        return web.json_response(self.expected_result)

    async def asyncTearDown(self) -> None:
        await self.server.close()

    async def validate_auth_requests(
        self,
        response_list: list[dict[str, int | float | str]],
        auth_request_list: list[dict[str, int | float | str]],
    ) -> None:
        assert len(response_list) == len(auth_request_list)
        if len(response_list) > 0:
            for response, auth_request in zip(response_list, auth_request_list):
                assert response["cscs_to_change"] == auth_request["cscs_to_change"]
                assert response["authorized_users"] == auth_request["authorized_users"]
                assert (
                    response["unauthorized_cscs"] == auth_request["unauthorized_cscs"]
                )

    async def test_get_approved_and_unprocessed_auth_requests(self) -> None:
        async with authorize.MinimalTestCsc(
            index=INDEX1
        ) as csc1, authorize.MinimalTestCsc(index=INDEX2) as csc2:
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            self.expected_result = APPROVED_AUTH_REQUESTS
            await self.handler.get_approved_and_unprocessed_auth_requests()
            await self.validate_auth_requests(
                response_list=self.handler.response,
                auth_request_list=self.expected_result,
            )

            # Remove any leading "+" or "-" from the user names and
            # unauthorized CSCs.
            expected_users1 = {
                val[1:].strip() if val[0] in "+-" else val.strip()
                for val in AUTH_USERS1.split(",")
            }
            expected_users2 = {
                val[1:].strip() if val[0] in "+-" else val.strip()
                for val in AUTH_USERS2.split(",")
            }
            expected_unauth_cscs1 = {
                val[1:].strip() if val[0] in "+-" else val.strip()
                for val in UNAUTH_CSCS1.split(",")
            }
            expected_unauth_cscs2 = {
                val[1:].strip() if val[0] in "+-" else val.strip()
                for val in UNAUTH_CSCS2.split(",")
            }

            expected_users_csc1 = expected_users1 | expected_users2
            expected_users_csc2 = expected_users2
            expected_unauth_cscs_csc1 = expected_unauth_cscs1 | expected_unauth_cscs2
            expected_unauth_cscs_csc2 = expected_unauth_cscs2

            assert csc1.salinfo.authorized_users == expected_users_csc1
            assert csc1.salinfo.non_authorized_cscs == expected_unauth_cscs_csc1
            assert csc2.salinfo.authorized_users == expected_users_csc2
            assert csc2.salinfo.non_authorized_cscs == expected_unauth_cscs_csc2

    async def test_handle_authorize_request(self) -> None:
        data = types.SimpleNamespace(
            authorizedUsers="test1@localhost,test3@localhost",
            cscsToChange="TestCSC1",
            nonAuthorizedCSCs="TestCSC2, TestCSC3:1",
            private_identity="RestAuthorizeHandlerTestCase",
        )
        self.expected_result = PENDING_AUTH_REQUEST
        await self.handler.handle_authorize_request(data)
        await self.validate_auth_requests(
            response_list=self.handler.response, auth_request_list=self.expected_result
        )
