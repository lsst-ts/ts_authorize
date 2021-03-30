# This file is part of ts_authorize.
#
# Developed for the LSST Telescope and Site Systems.
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
import logging
import shutil
import unittest

from lsst.ts import salobj
from lsst.ts import authorize

# Timeout for a long operation (sec), including waiting for Authorize
# to time out while trying to change a CSC.
STD_TIMEOUT = 60


class MinimalTestCsc(salobj.BaseCsc):
    """A mimial "Test" CSC that is not configurable.

    By being non-configurable it simplifies the conda build.
    """

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

    def do_setArrays(self, data):
        """Execute the setArrays command."""
        raise NotImplementedError()

    def do_setScalars(self, data):
        """Execute the setScalars command."""
        raise NotImplementedError()

    def do_fault(self, data):
        """Execute the fault command.

        Change the summary state to State.FAULT
        """
        self.log.warning("executing the fault command")
        self.fault(code=1, report="executing the fault command")

    async def do_wait(self, data):
        """Execute the wait command.

        Wait for the specified time and then acknowledge the command
        using the specified ack code.
        """
        self.assert_enabled()
        await asyncio.sleep(data.duration)


class AuthorizeTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        salobj.set_random_lsst_dds_domain()

    async def test_bin_script(self):
        exe_name = "run_authorization_service.py"
        exe_path = shutil.which(exe_name)
        if exe_path is None:
            self.fail(
                f"Could not find bin script {exe_name}; did you setup or install this package?"
            )

        process = await asyncio.create_subprocess_exec(exe_name)
        try:
            async with salobj.Domain() as domain, salobj.Remote(
                domain=domain, name="Authorize", index=None
            ) as remote:
                data = await remote.evt_logLevel.next(flush=False, timeout=STD_TIMEOUT)
                self.assertEqual(data.level, logging.INFO)
                await remote.evt_heartbeat.next(flush=False, timeout=STD_TIMEOUT)
                await remote.evt_heartbeat.next(flush=False, timeout=STD_TIMEOUT)

        finally:
            process.terminate()

    async def test_request_authorization_success(self):
        index1 = 5
        index2 = 52
        async with MinimalTestCsc(index=index1) as csc1, MinimalTestCsc(
            index=index2
        ) as csc2, authorize.Authorize() as auth, salobj.Remote(
            domain=auth.salinfo.domain, name="Authorize", index=None
        ) as remote:
            await remote.evt_logLevel.aget(timeout=STD_TIMEOUT)
            self.assertEqual(csc1.salinfo.authorized_users, set())
            self.assertEqual(csc1.salinfo.non_authorized_cscs, set())
            self.assertEqual(csc2.salinfo.authorized_users, set())
            self.assertEqual(csc2.salinfo.non_authorized_cscs, set())

            # Change the first Test CSC
            desired_users = ("sal@purview", "woof@123.456")
            desired_cscs = ("Foo", "Bar:1", "XKCD:47")
            await remote.cmd_requestAuthorization.set_start(
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
            # change it, that will time out, but the main command will
            # still succeed.
            await remote.cmd_requestAuthorization.set_start(
                cscsToChange=f"Test:{index1}, Test:{index2}, Test:999",
                authorizedUsers=", ".join(desired_users),
                nonAuthorizedCSCs=", ".join(desired_cscs),
                timeout=60,
            )
            self.assertEqual(csc1.salinfo.authorized_users, set(desired_users))
            self.assertEqual(csc1.salinfo.non_authorized_cscs, set(desired_cscs))
            self.assertEqual(csc2.salinfo.authorized_users, set(desired_users))
            self.assertEqual(csc2.salinfo.non_authorized_cscs, set(desired_cscs))

    async def test_request_authorization_errors(self):
        async with authorize.Authorize() as auth, salobj.Remote(
            domain=auth.salinfo.domain, name="Authorize", index=None
        ) as remote:
            with salobj.assertRaisesAckError():
                await remote.cmd_requestAuthorization.set_start(
                    cscsToChange="_bad_csc_name",
                    authorizedUsers="a@b",
                    nonAuthorizedCSCs="a",
                    timeout=STD_TIMEOUT,
                )
            with salobj.assertRaisesAckError():
                await remote.cmd_requestAuthorization.set_start(
                    cscsToChange="Test:2",
                    authorizedUsers="_bad_username@any",
                    nonAuthorizedCSCs="a",
                    timeout=STD_TIMEOUT,
                )
            with salobj.assertRaisesAckError():
                await remote.cmd_requestAuthorization.set_start(
                    cscsToChange="Test:2",
                    authorizedUsers="some@any",
                    nonAuthorizedCSCs="_badCscName",
                    timeout=STD_TIMEOUT,
                )


if __name__ == "__main__":
    unittest.main()
