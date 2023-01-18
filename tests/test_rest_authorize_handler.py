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

import os
import types
import unittest

import pytest
from lsst.ts import authorize, salobj
from lsst.ts.authorize.testutils import (
    APPROVED_AUTH_REQUESTS,
    APPROVED_PROCESSED_AUTH_REQUESTS,
    INDEX1,
    INDEX2,
    INVALID_AUTHLIST_PASSWORD,
    INVALID_AUTHLIST_USERNAME,
    PENDING_AUTH_REQUESTS,
    VALID_AUTHLIST_PASSWORD,
    VALID_AUTHLIST_USERNAME,
    get_token,
)


class RestAuthorizeHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        salobj.set_random_lsst_dds_partition_prefix()

        # SalObj Domain for the RestAuthorizeHandler.
        self.domain = salobj.Domain()
        # Configuration for the RestAuthorizeHandler.
        self.config = types.SimpleNamespace(
            host="localhost",
            port=5000,
        )

        # Prepare the username, password and token for authentication.
        os.environ["AUTHLIST_USER_NAME"] = VALID_AUTHLIST_USERNAME
        os.environ["AUTHLIST_USER_PASS"] = VALID_AUTHLIST_PASSWORD
        self.token = get_token()

    async def test_authenticate(self) -> None:
        async with authorize.MockWebServer(
            token=""
        ) as mock_web_server, authorize.RestAuthorizeHandler(
            domain=self.domain, config=self.config
        ) as handler:
            # Invalid authentication.
            valid_params = dict(
                token=get_token(),
                username=VALID_AUTHLIST_USERNAME,
                password=VALID_AUTHLIST_PASSWORD,
            )
            all_invalid_params = dict(
                token="",
                username=INVALID_AUTHLIST_USERNAME,
                password=INVALID_AUTHLIST_PASSWORD,
            )
            for name in ("token", "username", "password"):
                one_invalid_params = valid_params.copy()
                one_invalid_params[name] = all_invalid_params[name]
                mock_web_server.token = one_invalid_params["token"]
                handler.username = one_invalid_params["username"]
                handler.password = one_invalid_params["password"]
                with pytest.raises(RuntimeError):
                    await handler.authenticate()

            # Valid authentication.
            mock_web_server.token = self.token
            handler.username = VALID_AUTHLIST_USERNAME
            handler.password = VALID_AUTHLIST_PASSWORD
            await handler.authenticate()
            assert handler.response["data"]["token"] == self.token
            assert handler.token == self.token

    async def validate_auth_requests(
        self,
        response_list: list[authorize.RestMessageType],
        auth_request_list: list[authorize.RestMessageType],
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
        ) as csc1, authorize.MinimalTestCsc(
            index=INDEX2
        ) as csc2, authorize.MockWebServer(
            token=self.token
        ) as mock_web_server, authorize.RestAuthorizeHandler(
            domain=self.domain, config=self.config
        ) as handler:
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            for aar in APPROVED_AUTH_REQUESTS:
                mock_web_server.expected_rest_message = aar.rest_messages
                await handler.process_approved_and_unprocessed_auth_requests()
                await self.validate_auth_requests(
                    response_list=handler.response,
                    auth_request_list=mock_web_server.expected_rest_message,
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
                    mock_web_server.expected_execution_status
                    == APPROVED_PROCESSED_AUTH_REQUESTS[aar.rest_messages[-1]["id"]][
                        "execution_status"
                    ]
                )
                assert (
                    mock_web_server.expected_execution_message
                    == APPROVED_PROCESSED_AUTH_REQUESTS[aar.rest_messages[-1]["id"]][
                        "execution_message"
                    ]
                )

    async def test_handle_authorize_request(self) -> None:
        async with authorize.MockWebServer(
            token=self.token
        ) as mock_web_server, authorize.RestAuthorizeHandler(
            domain=self.domain, config=self.config
        ) as handler:
            for pending_auth_request in PENDING_AUTH_REQUESTS:
                mock_web_server.expected_rest_message = (
                    pending_auth_request.rest_messages
                )
                data = authorize.AuthRequestData(
                    authorized_users=pending_auth_request.rest_messages[0][
                        "authorized_users"
                    ],
                    cscs_to_change=pending_auth_request.rest_messages[0][
                        "cscs_to_change"
                    ],
                    non_authorized_cscs=pending_auth_request.rest_messages[0][
                        "unauthorized_cscs"
                    ],
                    private_identity="RestAuthorizeHandlerTestCase",
                )

                await handler.handle_authorize_request(data)
                await self.validate_auth_requests(
                    response_list=handler.response,
                    auth_request_list=mock_web_server.expected_rest_message,
                )
