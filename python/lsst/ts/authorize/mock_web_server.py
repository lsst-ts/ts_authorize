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

from aiohttp import web
from aiohttp.test_utils import TestServer

from .handler import AUTHLISTREQUEST_API, ID_EXECUTE_PARAMS, RestMessageTypeList
from .handler_utils import ExecutionStatus
from .testutils import APPROVED_PROCESSED_AUTH_REQUESTS


class MockWebServer:
    """Mock Web Server for unit tests."""

    def __init__(self) -> None:
        app = web.Application()
        app.router.add_get(AUTHLISTREQUEST_API, self.request_handler)
        app.router.add_post(AUTHLISTREQUEST_API, self.request_handler)
        app.router.add_put(
            AUTHLISTREQUEST_API + ID_EXECUTE_PARAMS, self.put_request_handler
        )
        self.server = TestServer(app=app, port=5000)
        # The expected result.
        self.expected_rest_message: RestMessageTypeList = []
        # The expected execution status.
        self.expected_execution_status = ExecutionStatus.PENDING
        # The expected execution message.
        self.expected_execution_message = ""

    async def request_handler(self, request: web.Request) -> web.Response:
        """General handler coroutine for the mock REST server."""
        return web.json_response(self.expected_rest_message)

    async def put_request_handler(self, request: web.Request) -> web.Response:
        """PUT handler coroutine for the mock REST server."""
        request_id = int(request.match_info["request_id"])
        response_dict = APPROVED_PROCESSED_AUTH_REQUESTS[request_id]
        req_json = await request.json()
        self.expected_execution_status = ExecutionStatus(req_json["execution_status"])
        self.expected_execution_message = req_json["execution_message"]
        return web.json_response(response_dict)
