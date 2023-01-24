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

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from types import TracebackType
from typing import Type

from aiohttp import web, web_exceptions
from aiohttp.test_utils import TestServer

from .handler import AUTHLISTREQUEST_ENDPOINT, GET_TOKEN_ENDPOINT, ID_EXECUTE_PARAMS
from .handler_utils import ExecutionStatus, RestMessageType
from .testutils import (
    APPROVED_PROCESSED_AUTH_REQUESTS,
    VALID_AUTHLIST_PASSWORD,
    VALID_AUTHLIST_USERNAME,
)


class MockWebServer:
    """Mock Web Server for unit tests."""

    def __init__(self, token: str) -> None:
        self.log = logging.getLogger(type(self).__name__)
        app = web.Application()
        app.add_routes(
            [
                web.get(AUTHLISTREQUEST_ENDPOINT, self.request_handler),
                web.post(AUTHLISTREQUEST_ENDPOINT, self.request_handler),
                web.post(GET_TOKEN_ENDPOINT, self.get_token_handler),
                web.put(
                    AUTHLISTREQUEST_ENDPOINT + ID_EXECUTE_PARAMS,
                    self.put_request_handler,
                ),
            ]
        )
        self.server = TestServer(app=app, port=5000)
        # The expected result.
        self.expected_rest_message: Iterable[RestMessageType] = []
        # The expected execution status.
        self.expected_execution_status = ExecutionStatus.PENDING
        # The expected execution message.
        self.expected_execution_message = ""
        # The token for authentication.
        self.token = token

    def __enter__(self) -> None:
        # This class only implements an async context manager.
        raise NotImplementedError("Use 'async with' instead.")

    def __exit__(
        self, type: Type[BaseException], value: BaseException, traceback: TracebackType
    ) -> None:
        # __exit__ should exist in pair with __enter__ but never be executed.
        raise NotImplementedError("Use 'async with' instead.")

    async def __aenter__(self) -> MockWebServer:
        await self.server.start_server()
        return self

    async def __aexit__(
        self, type: Type[BaseException], value: BaseException, traceback: TracebackType
    ) -> None:
        await self.server.close()

    async def verify_http_status(self, request: web.Request) -> None:
        """Verify that the requester has authenticated itself.

        Parameters
        ----------
        request : `web.Request`
            The web request to process.

        Raises
        ------
        web_exceptions.HTTPUnauthorized
            In case of missing or invalid credentials.
        """
        if (
            request.headers.get("Authorization") is None
            or request.headers.get("Authorization") != self.token
        ):
            raise web_exceptions.HTTPUnauthorized(
                body=json.dumps(
                    {"detail": ["Credentials were not provided or invalid."]}
                ),
                content_type="application/json",
            )

    async def request_handler(self, request: web.Request) -> web.Response:
        """General handler coroutine for the mock REST server.

        Parameters
        ----------
        request : `web.Request`
            The web request to process.
        """
        await self.verify_http_status(request=request)
        self.log.debug(f"Returning {self.expected_rest_message}")
        return web.json_response(self.expected_rest_message)

    async def put_request_handler(self, request: web.Request) -> web.Response:
        """PUT handler coroutine for the mock REST server.

        Parameters
        ----------
        request : `web.Request`
            The web request to process.
        """
        await self.verify_http_status(request=request)
        request_id = int(request.match_info["request_id"])
        response_dict = APPROVED_PROCESSED_AUTH_REQUESTS[request_id]
        req_json = await request.json()
        self.expected_execution_status = ExecutionStatus(req_json["execution_status"])
        self.expected_execution_message = req_json["execution_message"]
        self.log.debug(f"PUT returning {response_dict}")
        return web.json_response(response_dict)

    async def post_request_handler(self, request: web.Request) -> None:
        """POST handler coroutine for the mock REST server.

        Parameters
        ----------
        request : `web.Request`
            The web request to process.
        """
        await self.verify_http_status(request=request)

    async def get_token_handler(self, request: web.Request) -> web.Response:
        """POST handler coroutine for get token requests to the mock REST
        server.

        Parameters
        ----------
        request : `web.Request`
            The web request to process.

        Raises
        ------
        web_exceptions.HTTPBadRequest
            In case the provided credentials are incorrect.
        """
        req_json = await request.json()
        if (
            req_json["username"] == VALID_AUTHLIST_USERNAME
            and req_json["password"] == VALID_AUTHLIST_PASSWORD
            and self.token != ""
        ):
            data = {"token": self.token}
            self.log.debug(f"GET token returning {data}")
            return web.json_response(data)
        else:
            self.token = ""
            raise web_exceptions.HTTPBadRequest(
                body=json.dumps(
                    {
                        "non_field_errors": [
                            "Unable to log in with provided credentials."
                        ]
                    }
                ),
                content_type="application/json",
            )
