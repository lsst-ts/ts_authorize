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

from lsst.ts import authorize, salobj
from lsst.ts.authorize.testutils import INDEX1, INDEX2, NON_EXISTENT_CSC, TEST_DATA


class AutoAuthorizeHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_handle_authorize_request(self) -> None:
        salobj.set_random_lsst_dds_partition_prefix()
        domain = salobj.Domain()
        handler = authorize.handler.AutoAuthorizeHandler(domain=domain)

        async with authorize.MinimalTestCsc(
            index=INDEX1
        ) as csc1, authorize.MinimalTestCsc(index=INDEX2) as csc2:
            assert csc1.salinfo.authorized_users == set()
            assert csc1.salinfo.non_authorized_cscs == set()
            assert csc2.salinfo.authorized_users == set()
            assert csc2.salinfo.non_authorized_cscs == set()

            for td in TEST_DATA:
                data = authorize.AuthRequestData(
                    cscs_to_change=td.auth_request_data.cscs_to_change,
                    authorized_users=td.auth_request_data.authorized_users,
                    non_authorized_cscs=td.auth_request_data.non_authorized_cscs,
                    private_identity=td.auth_request_data.private_identity,
                )
                if NON_EXISTENT_CSC in td.auth_request_data.cscs_to_change:
                    with self.assertRaises(RuntimeError) as error:
                        await handler.handle_authorize_request(data=data)
                    cscs_to_command = authorize.set_from_comma_separated_string(
                        data.cscs_to_change
                    )
                    expected_message = authorize.create_failed_error_message(
                        csc_failed_messages=td.expected_failed_cscs,
                        cscs_succeeded=cscs_to_command - td.expected_failed_cscs.keys(),
                    )
                    self.assertEqual(str(error.exception), expected_message)
                else:
                    await handler.handle_authorize_request(data=data)
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
