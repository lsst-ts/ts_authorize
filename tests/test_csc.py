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
import pathlib
import typing
import unittest

from aiohttp import web
from aiohttp.test_utils import TestServer
from lsst.ts import authorize, salobj
from lsst.ts.authorize.testutils import (
    APPROVED_AUTH_REQUESTS,
    APPROVED_PROCESSED_AUTH_REQUESTS,
    INDEX1,
    INDEX2,
    NON_EXISTENT_CSC,
    PENDING_AUTH_REQUESTS,
    TEST_DATA,
)

# Timeout for a long operation (sec), including waiting for Authorize
# to time out while trying to change a CSC.
STD_TIMEOUT = 60

TEST_CONFIG_DIR = pathlib.Path(__file__).parent / "data" / "config"


class AuthorizeTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

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

    def basic_make_csc(
        self,
        initial_state: salobj.State,
        config_dir: str,
        override: str = "",
        **kwargs: typing.Any,
    ) -> None:
        return authorize.Authorize(
            initial_state=initial_state,
            config_dir=config_dir,
            override=override,
        )

    async def test_standard_state_transitions(self) -> None:
        """Test standard CSC state transitions.

        The initial state is STANDBY.
        The standard commands and associated state transitions are:

        * start: STANDBY to DISABLED
        * enable: DISABLED to ENABLED

        * disable: ENABLED to DISABLED
        * standby: DISABLED to STANDBY
        * exitControl: STANDBY, FAULT to OFFLINE (quit)
        """

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.STANDBY,
        ):
            await self.check_standard_state_transitions(
                enabled_commands=("requestAuthorization",)
            )

    async def test_bin_script(self) -> None:
        await self.check_bin_script(
            name="Authorize",
            index=None,
            exe_name="run_authorize",
        )

    async def test_request_auto_authorization_success(self) -> None:
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
        ), authorize.MinimalTestCsc(index=INDEX1) as csc1, authorize.MinimalTestCsc(
            index=INDEX2
        ) as csc2:
            await self.remote.evt_logLevel.aget(timeout=STD_TIMEOUT)
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            for td in TEST_DATA:
                data = {
                    "cscsToChange": td.auth_request_data.cscs_to_change,
                    "authorizedUsers": td.auth_request_data.authorized_users,
                    "nonAuthorizedCSCs": td.auth_request_data.non_authorized_cscs,
                    "timeout": STD_TIMEOUT,
                }
                if NON_EXISTENT_CSC in td.auth_request_data.cscs_to_change:
                    with salobj.assertRaisesAckError():
                        await self.remote.cmd_requestAuthorization.set_start(**data)
                else:
                    await self.remote.cmd_requestAuthorization.set_start(**data)
                assert csc1.salinfo.authorized_users == td.expected_authorized_users[0]
                assert (
                    csc1.salinfo.non_authorized_cscs
                    == td.expected_non_authorized_cscs[0]
                )
                assert csc2.salinfo.authorized_users == td.expected_authorized_users[1]
                assert (
                    csc2.salinfo.non_authorized_cscs
                    == td.expected_non_authorized_cscs[1]
                )

    async def test_request_auto_authorization_errors(self) -> None:
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
        ):
            with salobj.assertRaisesAckError():
                # Empty cscsToChange
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange="",
                    authorizedUsers="a@b",
                    nonAuthorizedCSCs="a",
                    timeout=STD_TIMEOUT,
                )
            with salobj.assertRaisesAckError():
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange="_bad_csc_name",
                    authorizedUsers="a@b",
                    nonAuthorizedCSCs="a",
                    timeout=STD_TIMEOUT,
                )
            with salobj.assertRaisesAckError():
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange="Test:2",
                    authorizedUsers="_bad_username@any",
                    nonAuthorizedCSCs="a",
                    timeout=STD_TIMEOUT,
                )
            with salobj.assertRaisesAckError():
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange="Test:2",
                    authorizedUsers="some@any",
                    nonAuthorizedCSCs="_badCscName",
                    timeout=STD_TIMEOUT,
                )

    async def test_request_rest_authorization(self) -> None:
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
            override="test_rest_config.yaml",
        ), authorize.MinimalTestCsc(index=INDEX1) as csc1, authorize.MinimalTestCsc(
            index=INDEX2
        ) as csc2:
            td = TEST_DATA[0]
            self.expected_rest_message = PENDING_AUTH_REQUESTS[0].rest_messages
            data = {
                "cscsToChange": td.auth_request_data.cscs_to_change,
                "authorizedUsers": td.auth_request_data.authorized_users,
                "nonAuthorizedCSCs": td.auth_request_data.non_authorized_cscs,
                "timeout": STD_TIMEOUT,
            }
            await self.remote.cmd_requestAuthorization.set_start(**data)

            # These should not have changed because the requests have been
            # sent to the REST server and will not have been sent to the
            # CSCs yet.
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            assert self.csc.authorize_handler.response == self.expected_rest_message

    async def test_process_approved_and_unprocessed_auth_requests(self) -> None:
        aar = APPROVED_AUTH_REQUESTS[0]
        self.expected_rest_message = [aar.rest_messages[1]]

        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
            override="test_rest_config.yaml",
        ), authorize.MinimalTestCsc(index=INDEX1) as csc1, authorize.MinimalTestCsc(
            index=INDEX2
        ) as csc2:

            # Give time to the CSC to process the REST messages.
            while csc1.salinfo.authorized_users == set():
                await asyncio.sleep(0.5)

            # These should not have changed because the requests have been
            # sent to the REST server and will not have been sent to the
            # CSCs yet.
            assert csc1.salinfo.authorized_users == aar.expected_authorized_users[1]
            assert (
                csc1.salinfo.non_authorized_cscs == aar.expected_non_authorized_cscs[1]
            )
            assert csc2.salinfo.authorized_users == aar.expected_authorized_users[1]
            assert (
                csc2.salinfo.non_authorized_cscs == aar.expected_non_authorized_cscs[1]
            )

            assert self.csc.authorize_handler.response == self.expected_rest_message
