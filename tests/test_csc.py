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
        index1 = 5
        index2 = 52
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
        ), authorize.MinimalTestCsc(index=index1) as csc1, authorize.MinimalTestCsc(
            index=index2
        ) as csc2:
            await self.remote.evt_logLevel.aget(timeout=STD_TIMEOUT)
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            # Change the first Test CSC
            desired_users = {"sal@purview", "woof@123.456"}
            desired_cscs = {"Foo", "Bar:1", "XKCD:47"}
            await self.remote.cmd_requestAuthorization.set_start(
                cscsToChange=f"Test:{index1}",
                authorizedUsers=", ".join(desired_users),
                nonAuthorizedCSCs=", ".join(desired_cscs),
                timeout=STD_TIMEOUT,
            )
            assert csc1.salinfo.authorized_users == desired_users
            assert csc1.salinfo.non_authorized_cscs == desired_cscs
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            # Change both Test CSCs
            desired_users = {"meow@validate", "v122s@123"}
            desired_cscs = {"AT", "seisen:22"}
            # Include a CSC that does not exist. Authorize will try to
            # change it, that will time out, command will fail but other CSCs
            # will be set.
            with salobj.assertRaisesAckError():
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange=f"Test:{index1}, Test:999, Test:{index2}",
                    authorizedUsers=", ".join(desired_users),
                    nonAuthorizedCSCs=", ".join(desired_cscs),
                    timeout=STD_TIMEOUT,
                )
            assert csc1.salinfo.authorized_users == desired_users
            assert csc1.salinfo.non_authorized_cscs == desired_cscs
            assert csc2.salinfo.authorized_users == desired_users
            assert csc2.salinfo.non_authorized_cscs == desired_cscs

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
