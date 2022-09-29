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

import pathlib
import typing
import unittest

from auth_request_data import INDEX1, INDEX2, NON_EXISTENT_CSC, TEST_DATA
from lsst.ts import authorize, salobj

# Timeout for a long operation (sec), including waiting for Authorize
# to time out while trying to change a CSC.
STD_TIMEOUT = 60

TEST_CONFIG_DIR = pathlib.Path(__file__).parent / "data" / "config"


class AuthorizeTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
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
                    "cscsToChange": td.cscs_to_command,
                    "authorizedUsers": td.authorized_users,
                    "nonAuthorizedCSCs": td.non_authorized_cscs,
                    "timeout": STD_TIMEOUT,
                }
                if NON_EXISTENT_CSC in td.cscs_to_command:
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
