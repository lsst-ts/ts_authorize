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
import unittest

from lsst.ts import salobj
from lsst.ts import authorize

# Timeout for a long operation (sec), including waiting for Authorize
# to time out while trying to change a CSC.
STD_TIMEOUT = 60

TEST_CONFIG_DIR = pathlib.Path(__file__).parent / "data" / "config"


class MinimalTestCsc(salobj.BaseCsc):
    """A mimial "Test" CSC that is not configurable.

    By being non-configurable it simplifies the conda build.
    """

    version = "?"
    valid_simulation_modes = [0]

    def __init__(
        self,
        index,
        config_dir=None,
        initial_state=salobj.State.STANDBY,
        simulation_mode=0,
    ):
        super().__init__(
            name="Test",
            index=index,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

    async def do_setArrays(self, data):
        """Execute the setArrays command."""
        raise NotImplementedError()

    async def do_setScalars(self, data):
        """Execute the setScalars command."""
        raise NotImplementedError()

    async def do_fault(self, data):
        """Execute the fault command.

        Change the summary state to State.FAULT
        """
        self.log.warning("executing the fault command")
        await self.fault(code=1, report="executing the fault command")

    async def do_wait(self, data):
        """Execute the wait command.

        Wait for the specified time and then acknowledge the command
        using the specified ack code.
        """
        self.assert_enabled()
        await asyncio.sleep(data.duration)


class AuthorizeTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, config_dir, **kwargs):
        return authorize.Authorize(
            initial_state=initial_state,
            config_dir=config_dir,
        )

    async def test_standard_state_transitions(self):
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

    async def test_bin_script(self):
        await self.check_bin_script(
            name="Authorize",
            index=None,
            exe_name="run_authorize",
        )

    async def test_request_authorization_success(self):
        index1 = 5
        index2 = 52
        async with self.make_csc(
            config_dir=TEST_CONFIG_DIR,
            initial_state=salobj.State.ENABLED,
        ), MinimalTestCsc(index=index1) as csc1, MinimalTestCsc(index=index2) as csc2:
            await self.remote.evt_logLevel.aget(timeout=STD_TIMEOUT)
            self.assertEqual(csc1.salinfo.authorized_users, set())
            self.assertEqual(csc1.salinfo.non_authorized_cscs, set())
            self.assertEqual(csc2.salinfo.authorized_users, set())
            self.assertEqual(csc2.salinfo.non_authorized_cscs, set())

            # Change the first Test CSC
            desired_users = ("sal@purview", "woof@123.456")
            desired_cscs = ("Foo", "Bar:1", "XKCD:47")
            await self.remote.cmd_requestAuthorization.set_start(
                cscsToChange=f"Test:{index1}",
                authorizedUsers=", ".join(desired_users),
                nonAuthorizedCSCs=", ".join(desired_cscs),
                timeout=60,
            )
            self.assertEqual(csc1.salinfo.authorized_users, set(desired_users))
            self.assertEqual(csc1.salinfo.non_authorized_cscs, set(desired_cscs))
            self.assertEqual(csc2.salinfo.authorized_users, set())
            self.assertEqual(csc2.salinfo.non_authorized_cscs, set())

            # Change both Test CSCs
            desired_users = ("meow@validate", "v122s@123")
            desired_cscs = ("AT", "seisen:22")
            # Include a CSC that does not exist. Authorize will try to
            # change it, that will time out, command will fail but other CSCs
            # will be set.
            with salobj.assertRaisesAckError():
                await self.remote.cmd_requestAuthorization.set_start(
                    cscsToChange=f"Test:{index1}, Test:999, Test:{index2}",
                    authorizedUsers=", ".join(desired_users),
                    nonAuthorizedCSCs=", ".join(desired_cscs),
                    timeout=60,
                )
            self.assertEqual(csc1.salinfo.authorized_users, set(desired_users))
            self.assertEqual(csc1.salinfo.non_authorized_cscs, set(desired_cscs))
            self.assertEqual(csc2.salinfo.authorized_users, set(desired_users))
            self.assertEqual(csc2.salinfo.non_authorized_cscs, set(desired_cscs))

    async def test_request_authorization_errors(self):
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


if __name__ == "__main__":
    unittest.main()
