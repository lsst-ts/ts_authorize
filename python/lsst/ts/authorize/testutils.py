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

import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from .handler_utils import AuthRequestData, ExecutionStatus, RestMessageType

# Indices to be used for Test CSCs.
INDEX1 = 5
INDEX2 = 52

# A non-existent user.
NON_EXISTENT_USER = "foo@bar.com"
# A non-existent CSC.
NON_EXISTENT_CSC = "Test:999"

# Several sets of test users.
TEST_USERS_1 = {f"test{i}@localhost" for i in range(2)}
TEST_USERS_2 = {f"another_test{i}@localhost" for i in range(2)}
USERS_TO_REMOVE = {"test2@loclahost", "another_test1@localhost", NON_EXISTENT_USER}
JOINED_TEST_USERS = TEST_USERS_1 | TEST_USERS_2
REMAINING_USERS = JOINED_TEST_USERS - USERS_TO_REMOVE

# Several sets of test CSCs.
TEST_CSCS_1 = {"DIMM", "ESS:1", "GenericCamera:47"}
TEST_CSCS_2 = {"ATDome", "ScriptQueue:22"}
CSCS_TO_REMOVE = {"GenericCamera:47", "ATDome", NON_EXISTENT_CSC}
JOINED_TEST_CSCS = TEST_CSCS_1 | TEST_CSCS_2
REMAINING_CSCS = JOINED_TEST_CSCS - CSCS_TO_REMOVE

# Valid authentication data.
VALID_AUTHLIST_USERNAME = "test1@localhost"
VALID_AUTHLIST_PASSWORD = "test12345678"

# Invalid authentication data.
INVALID_AUTHLIST_USERNAME = "test2@localhost"
INVALID_AUTHLIST_PASSWORD = "test2468"


# A LOVE authentication token has 40 characters so `token_hex` needs to
# randomly select 20 bytes since each byte gets decoded to 2 hex characters.
def get_token() -> str:
    return secrets.token_hex(20)


class RequestStatus(str, Enum):
    APPROVED = "Approved"
    PENDING = "Pending"


@dataclass
class AuthRequestTestData:
    """DataClass representing test data for auth request tests."""

    auth_request_data: AuthRequestData
    expected_authorized_users: list[set[str]]
    expected_non_authorized_cscs: list[set[str]]
    expected_failed_cscs: dict[str, str]


@dataclass
class RestMessage:
    """DataClass representing a message as returned by the REST server."""

    id: int
    cscs_to_change: str
    authorized_users: str
    unauthorized_cscs: str
    status: str
    execution_status: str
    execution_message: str
    resolved_by: str = "operator1@localhost"
    user: str = "team_leader1@localhost"
    requested_by: str = "team_leader1@localhost"
    requested_at: str = "2022-09-01T11:10:00.000Z"
    duration: int = 60
    resolved_at: str = "2022-09-01T11:15:00.000Z"

    @classmethod
    def from_auth_request_data(
        cls,
        artd: AuthRequestTestData,
        message_id: int,
        status: str,
        execution_status: str = ExecutionStatus.PENDING.value,
        execution_message: str = "",
    ) -> RestMessageType:
        """Factory method that takes values for part of the variables from the
        provided `AuthRequestTestData` instance.

        Parameters
        ----------
        artd : `AuthRequestTestData`
            The instance to take values from.
        message_id : `int`
            The ID of the RestMessage.
        status : `str`
            The status of the RestMessage.
        execution_status : `str`
            The execution status of the RestMessage. Defaults to
            `ExecutionState`.`PENDING`.
        execution_message : `str`
            The execution message of the RestMessage. Defaults to an empty
            string.

        Returns
        -------

        """
        return vars(
            cls(
                id=message_id,
                cscs_to_change=artd.auth_request_data.cscs_to_change,
                authorized_users=artd.auth_request_data.authorized_users,
                unauthorized_cscs=artd.auth_request_data.non_authorized_cscs,
                status=status,
                execution_status=execution_status,
                execution_message=execution_message,
            )
        )


@dataclass
class RestMessageData:
    rest_messages: Iterable[RestMessageType]
    expected_authorized_users: list[set[str]]
    expected_non_authorized_cscs: list[set[str]]
    expected_failed_cscs: dict[str, str]


TEST_DATA = [
    # A set of authorized users and non-authorized CSCs to be sent to a single
    # CSC.
    AuthRequestTestData(
        auth_request_data=AuthRequestData(
            authorized_users=", ".join(TEST_USERS_1),
            cscs_to_change=f"Test:{INDEX1}",
            non_authorized_cscs=", ".join(TEST_CSCS_1),
            private_identity="operator1@localhost",
        ),
        expected_authorized_users=[TEST_USERS_1, set()],
        expected_non_authorized_cscs=[TEST_CSCS_1, set()],
        expected_failed_cscs={},
    ),
    # A set of authorized users and non-authorized CSCs to be sent to two CSCs.
    # Since no "+" or "-" are present, the existing authorized users and
    # non-authorized CSCs will be replaced.
    AuthRequestTestData(
        auth_request_data=AuthRequestData(
            authorized_users=", ".join(TEST_USERS_2),
            cscs_to_change=f"Test:{INDEX1}, {NON_EXISTENT_CSC}, Test:{INDEX2}",
            non_authorized_cscs=", ".join(TEST_CSCS_2),
            private_identity="operator1@localhost",
        ),
        expected_authorized_users=[TEST_USERS_2, TEST_USERS_2],
        expected_non_authorized_cscs=[TEST_CSCS_2, TEST_CSCS_2],
        expected_failed_cscs={
            NON_EXISTENT_CSC: "Timed out waiting for command acknowledgement"
        },
    ),
    # Here we use a "+" for both the authorized users and the non-authorized
    # CSCs, meaning that they get added to the existing sets.
    AuthRequestTestData(
        auth_request_data=AuthRequestData(
            authorized_users="+" + ", ".join(TEST_USERS_1),
            cscs_to_change=f"Test:{INDEX1}, Test:{INDEX2}",
            non_authorized_cscs="+" + ", ".join(TEST_CSCS_1),
            private_identity="operator1@localhost",
        ),
        expected_authorized_users=[JOINED_TEST_USERS, JOINED_TEST_USERS],
        expected_non_authorized_cscs=[JOINED_TEST_CSCS, JOINED_TEST_CSCS],
        expected_failed_cscs={},
    ),
    # Here we use a "-" for both the authorized users and the non-authorized
    # CSCs, meaning that they get removed from the existing sets.
    AuthRequestTestData(
        auth_request_data=AuthRequestData(
            authorized_users="-" + ", ".join(USERS_TO_REMOVE),
            cscs_to_change=f"Test:{INDEX1}, Test:{INDEX2}",
            non_authorized_cscs="-" + ", ".join(CSCS_TO_REMOVE),
            private_identity="operator1@localhost",
        ),
        expected_authorized_users=[REMAINING_USERS, REMAINING_USERS],
        expected_non_authorized_cscs=[REMAINING_CSCS, REMAINING_CSCS],
        expected_failed_cscs={},
    ),
]


# A list representing a single pending, unprocessed authorize request.
PENDING_AUTH_REQUESTS = [
    RestMessageData(
        rest_messages=[
            RestMessage.from_auth_request_data(
                artd=TEST_DATA[0], message_id=0, status=RequestStatus.PENDING.value
            ),
        ],
        expected_authorized_users=TEST_DATA[0].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[0].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[0].expected_failed_cscs,
    )
]

# A list of single and multiple approved, unprocessed authorization requests.
APPROVED_AUTH_REQUESTS = [
    RestMessageData(
        rest_messages=[
            RestMessage.from_auth_request_data(
                artd=TEST_DATA[0], message_id=0, status=RequestStatus.APPROVED.value
            ),
            RestMessage.from_auth_request_data(
                artd=TEST_DATA[1], message_id=1, status=RequestStatus.APPROVED.value
            ),
        ],
        expected_authorized_users=TEST_DATA[1].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[1].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[1].expected_failed_cscs,
    ),
    RestMessageData(
        rest_messages=[
            RestMessage.from_auth_request_data(
                artd=TEST_DATA[2], message_id=2, status=RequestStatus.APPROVED.value
            ),
        ],
        expected_authorized_users=TEST_DATA[2].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[2].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[2].expected_failed_cscs,
    ),
    RestMessageData(
        rest_messages=[
            RestMessage.from_auth_request_data(
                artd=TEST_DATA[3], message_id=3, status=RequestStatus.APPROVED.value
            ),
        ],
        expected_authorized_users=TEST_DATA[3].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[3].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[3].expected_failed_cscs,
    ),
]

# A list of approved, processed authorization requests.
APPROVED_PROCESSED_AUTH_REQUESTS = [
    RestMessage.from_auth_request_data(
        artd=TEST_DATA[0],
        message_id=0,
        status=RequestStatus.APPROVED.value,
        execution_status=ExecutionStatus.SUCCESSFUL.value,
        execution_message="The following CSCs were updated correctly: Test:5.",
    ),
    RestMessage.from_auth_request_data(
        artd=TEST_DATA[1],
        message_id=1,
        status=RequestStatus.APPROVED.value,
        execution_status=ExecutionStatus.FAILED.value,
        execution_message="The following CSCs were updated correctly: Test:5, Test:52. "
        + "The following CSCs failed to update correctly: Test:999.",
    ),
    RestMessage.from_auth_request_data(
        artd=TEST_DATA[2],
        message_id=2,
        status=RequestStatus.APPROVED.value,
        execution_status=ExecutionStatus.SUCCESSFUL.value,
        execution_message="The following CSCs were updated correctly: Test:5, Test:52.",
    ),
    RestMessage.from_auth_request_data(
        artd=TEST_DATA[3],
        message_id=3,
        status=RequestStatus.APPROVED.value,
        execution_status=ExecutionStatus.SUCCESSFUL.value,
        execution_message="The following CSCs were updated correctly: Test:5, Test:52.",
    ),
]

# A list representing a single pending, unprocessed authorize request for
# incorrect CSCs or authorized users.
FAULTY_PENDING_AUTH_REQUESTS = [
    {
        "id": 1,
        "resolved_by": "cmd_user",
        "user": "cmd_user",
        "cscs_to_change": "MTQueue",
        "authorized_users": "+test@localhost",
        "unauthorized_cscs": "",
        "requested_by": "test@localhost",
        "requested_at": "2022-09-01T11:10:00.000Z",
        "duration": None,
        "message": "testing",
        "status": "Authorized",
        "execution_status": "Pending",
        "execution_message": None,
        "resolved_at": "2022-09-01T11:15:00.000Z",
    },
    {
        "id": 2,
        "resolved_by": "cmd_user",
        "user": "cmd_user",
        "cscs_to_change": "Test:5",
        "authorized_users": "test",
        "unauthorized_cscs": "",
        "requested_by": "test@localhost",
        "requested_at": "2022-09-01T11:10:00.000Z",
        "duration": None,
        "message": "testing",
        "status": "Authorized",
        "execution_status": "Pending",
        "execution_message": None,
        "resolved_at": "2022-09-01T11:15:00.000Z",
    },
]

# The expected execution messages for the faulty pending auth requests.
EXP_EXEC_MSGS_FOR_FAULTY_REQS = [
    "The following CSCs were updated correctly: None. "
    "The following CSCs failed to update correctly: MTQueue.",
    "The following CSCs were updated correctly: None. "
    "The following CSCs failed to update correctly: Test:5.",
]
