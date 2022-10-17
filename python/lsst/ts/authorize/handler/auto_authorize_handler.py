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

__all__ = ["AutoAuthorizeHandler"]

from ..handler_utils import AuthRequestData
from .base_authorize_handler import BaseAuthorizeHandler


class AutoAuthorizeHandler(BaseAuthorizeHandler):
    async def handle_authorize_request(self, data: AuthRequestData) -> None:
        """Handle an authorize request. Contact each CSC in the request and
        send the setAuthList command.

        Parameters
        ----------
        data : `salobj.type_hints.BaseMsgType`
            The data containing the authorize request as described in the
            corresponding xml file in ts_xml.

        Raises
        ------
        RuntimeError
            Raised in case at least one of the CSCs cannot be contacted.

        Notes
        -----
        All CSCs that can be contacted get changed, even if one or more CSCs
        cannot be contacted.
        """
        await self.process_authorize_request(data=data)

        if len(self.csc_failed_messages) > 0:
            raise RuntimeError(
                f"Failed to set authList for the following CSCs: {self.csc_failed_messages}. "
                f"The following CSCs were successfully updated: {self.cscs_succeeded}."
            )
