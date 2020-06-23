# This file is part of ts_authorize.
#
# Developed for the LSST Data Management System.
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
from . import utils

# Timeout for authorization command (seconds)
AUTH_TIMEOUT = 5

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 1


class Authorize(salobj.Controller):
    def __init__(self):
        super().__init__(name="Authorize", index=None, do_callbacks=True)
        # Allow anyone to issue the requestAuthorization command.
        self.cmd_requestAuthorization.authorize = False
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

    async def heartbeat_loop(self):
        try:
            while True:
                self.evt_heartbeat.put()
                await asyncio.sleep(self.heartbeat_interval)
        except asyncio.CancelledError:
            pass
        except Exception:
            self.log.exception("Heartbeat loop failed")

    async def do_requestAuthorization(self, data):
        """Implement the requestAuthorization command.

        Parameters
        ----------
        data : ``cmd_requestAuthorization.DataType``
            Command data.
        """
        # Check values
        cscs_to_command = [val.strip() for val in data.cscsToChange.split(",")]
        if not cscs_to_command:
            self.log.warning(
                "No CSCs specified in cscsToChange; command has no effect."
            )
            return
        for csc in cscs_to_command:
            utils.check_csc(csc)

        auth_users = data.authorizedUsers
        if auth_users:
            if auth_users[0] in ("+", "-"):
                auth_users = auth_users[1:]
            for user in auth_users.split(","):
                utils.check_user_host(user.strip())

        nonauth_cscs = data.nonAuthorizedCSCs
        if nonauth_cscs:
            if nonauth_cscs[0] in ("+", "-"):
                nonauth_cscs = nonauth_cscs[1:]
            for csc in nonauth_cscs.split(","):
                utils.check_csc(csc.strip())

        for csc_name_index in cscs_to_command:
            csc, index = salobj.name_to_name_index(csc_name_index)
            try:
                async with salobj.Remote(
                    domain=self.salinfo.domain, name=csc, index=index, include=[]
                ) as remote:
                    await remote.cmd_setAuthList.set_start(
                        authorizedUsers=data.authorizedUsers,
                        nonAuthorizedCSCs=data.nonAuthorizedCSCs,
                        timeout=AUTH_TIMEOUT,
                    )
                self.log.info(f"Set authList for {csc_name_index}")
            except salobj.AckError as e:
                self.log.warn(
                    f"Failed to set authList for {csc_name_index}: {e.args[0]}"
                )
