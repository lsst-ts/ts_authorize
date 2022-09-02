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

from lsst.ts import salobj


class MinimalTestCsc(salobj.BaseCsc):
    """A mimial "Test" CSC that is not configurable.

    By being non-configurable it simplifies the conda build.
    """

    version = "?"
    valid_simulation_modes = [0]

    def __init__(
        self,
        index: int,
        config_dir: None | str = None,
        initial_state: salobj.State = salobj.State.STANDBY,
        simulation_mode: int = 0,
    ) -> None:
        super().__init__(
            name="Test",
            index=index,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )

    async def do_setArrays(self, data: salobj.type_hints.BaseMsgType) -> None:
        """Execute the setArrays command."""
        raise NotImplementedError()

    async def do_setScalars(self, data: salobj.type_hints.BaseMsgType) -> None:
        """Execute the setScalars command."""
        raise NotImplementedError()

    async def do_fault(self, data: salobj.type_hints.BaseMsgType) -> None:
        """Execute the fault command.

        Change the summary state to State.FAULT
        """
        self.log.warning("executing the fault command")
        await self.fault(code=1, report="executing the fault command")

    async def do_wait(self, data: salobj.type_hints.BaseMsgType) -> None:
        """Execute the wait command.

        Wait for the specified time and then acknowledge the command
        using the specified ack code.
        """
        self.assert_enabled()
        await asyncio.sleep(data.duration)
