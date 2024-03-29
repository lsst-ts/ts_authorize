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

import pytest
from lsst.ts import authorize


class UtilsTestCase(unittest.TestCase):
    def test_check_cscs(self) -> None:
        good_values = {
            "MTDome",
            "ScriptQueue:0",
            "ESS:1",
            "DIMM:56789",
        }
        authorize.check_cscs(good_values)

        for bad_prefix in ("_", ".", "-", "?", "*"):
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"{bad_prefix}MTDome"})
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"{bad_prefix}ESS:1"})

        for bad_char in (".", "-", "?", "*", "@"):
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"MTDome{bad_char}"})
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"ESS{bad_char}:1"})

        for bad_index_char in ("a", "Z", ".", "-", "?", "*", "@"):
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"ESS:{bad_index_char}"})
            with self.assertRaises(ValueError):
                authorize.check_cscs({f"ESS:1{bad_index_char}"})

        for csc_names in [{"ABC"}, {"ABC:1"}, {"ABC:1", "ABC:2"}]:
            with pytest.raises(ValueError, match="Unknown CSCs: ABC"):
                authorize.check_cscs(csc_names)

    def test_check_user_hosts(self) -> None:
        good_values = {
            "abc_ABC-123.xyz@abc_ABC-123.xyz",
            "abc_ABC-123.xyz@127.64.34.5",
        }
        authorize.check_user_hosts(good_values)

        for bad_prefix in ("_", ".", "-", "@", "?", "*"):
            with self.assertRaises(ValueError):
                authorize.check_user_hosts({f"{bad_prefix}abc@123"})
            with self.assertRaises(ValueError):
                authorize.check_user_hosts({f"abc@{bad_prefix}123"})

        for bad_char in ("@", "?", "*"):
            with self.assertRaises(ValueError):
                authorize.check_user_hosts({f"abc{bad_char}@123"})
            with self.assertRaises(ValueError):
                authorize.check_user_hosts({f"abc@{bad_char}123"})


if __name__ == "__main__":
    unittest.main()
