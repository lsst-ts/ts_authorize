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

__all__ = ["BaseAuthorizeHandler"]

import logging
from abc import ABC, abstractmethod

from lsst.ts import salobj


class BaseAuthorizeHandler(ABC):
    def __init__(
        self, log: logging.Logger = None, domain: salobj.Domain = None
    ) -> None:
        if log is not None:
            self.log = log.getChild(str(self))
        else:
            self.log = logging.getLogger(str(self))
        self.domain = domain

    @abstractmethod
    async def handle_authorize_request(
        self, data: salobj.type_hints.BaseMsgType
    ) -> None:
        raise NotImplementedError
