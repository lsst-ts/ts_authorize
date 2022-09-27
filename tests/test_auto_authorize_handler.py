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

import unittest
from types import SimpleNamespace

from lsst.ts import authorize, salobj


class AutoAuthorizeHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_handle_authorize_request(self) -> None:
        salobj.set_random_lsst_dds_partition_prefix()
        domain = salobj.Domain()
        handler = authorize.handler.AutoAuthorizeHandler(domain=domain)

        index1 = 5
        index2 = 52
        async with authorize.MinimalTestCsc(
            index=index1
        ) as csc1, authorize.MinimalTestCsc(index=index2) as csc2:
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            # Change the first Test CSC
            desired_users = {"sal@purview", "woof@123.456"}
            desired_cscs = {"Foo", "Bar:1", "XKCD:47"}
            data = SimpleNamespace(
                cscsToChange=f"Test:{index1}",
                authorizedUsers=", ".join(desired_users),
                nonAuthorizedCSCs=", ".join(desired_cscs),
            )
            await handler.handle_authorize_request(data=data)
            assert csc1.salinfo.authorized_users == desired_users
            assert csc1.salinfo.non_authorized_cscs == desired_cscs
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            # Change both Test CSCs
            desired_users = {"meow@validate", "v122s@123"}
            desired_cscs = {"AT", "seisen:22"}
            # Include a CSC that does not exist. The handler will try to
            # change it, that will time out, command will fail but other CSCs
            # will be set.
            data = SimpleNamespace(
                cscsToChange=f"Test:{index1}, Test:999, Test:{index2}",
                authorizedUsers=", ".join(desired_users),
                nonAuthorizedCSCs=", ".join(desired_cscs),
            )
            with self.assertRaises(RuntimeError):
                await handler.handle_authorize_request(data=data)
            assert csc1.salinfo.authorized_users == desired_users
            assert csc1.salinfo.non_authorized_cscs == desired_cscs
            assert csc2.salinfo.authorized_users == desired_users
            assert csc2.salinfo.non_authorized_cscs == desired_cscs
            assert len(handler.csc_failed_messages) == 1
            assert "Test:999" in handler.csc_failed_messages.keys()
