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

from dataclasses import asdict, dataclass

from lsst.ts.authorize.handler import RestMessageType, RestMessageTypeList

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
TEST_CSCS_1 = {"Foo", "Bar:1", "XKCD:47"}
TEST_CSCS_2 = {"AT", "seisen:22"}
CSCS_TO_REMOVE = {"XKCD:47", "AT", NON_EXISTENT_CSC}
JOINED_TEST_CSCS = TEST_CSCS_1 | TEST_CSCS_2
REMAINING_CSCS = JOINED_TEST_CSCS - CSCS_TO_REMOVE

# ID for the RestMessage instances
message_id = 0


@dataclass
class AuthRequestData:
    """DataClass representing test data for auth request tests."""

    cscs_to_command: str
    authorized_users: str
    non_authorized_cscs: str
    expected_authorized_users: list[set[str]]
    expected_non_authorized_cscs: list[set[str]]
    expected_failed_cscs: set[str]


@dataclass
class RestMessage:
    """DataClass representing a message as returned by the REST server."""

    id: int
    cscs_to_change: str
    authorized_users: str
    unauthorized_cscs: str
    status: str
    resolved_by: str = "operator1@localhost"
    user: str = "team_leader1@localhost"
    requested_by: str = "team_leader1@localhost"
    requested_at: str = "2022-09-01T11:10:00.000Z"
    duration: int = 60
    message: str = "Test message."
    resolved_at: str = "2022-09-01T11:15:00.000Z"


@dataclass
class RestMessageData:
    rest_messages: RestMessageTypeList
    expected_authorized_users: list[set[str]]
    expected_non_authorized_cscs: list[set[str]]
    expected_failed_cscs: set[str]


TEST_DATA = [
    # A set of authorized users and non-authorized CSCs to be sent to a single
    # CSC.
    AuthRequestData(
        cscs_to_command=f"Test:{INDEX1}",
        authorized_users=", ".join(TEST_USERS_1),
        non_authorized_cscs=", ".join(TEST_CSCS_1),
        expected_authorized_users=[TEST_USERS_1, set()],
        expected_non_authorized_cscs=[TEST_CSCS_1, set()],
        expected_failed_cscs=set(),
    ),
    # A set of authorized users and non-authorized CSCs to be sent to two CSCs.
    # Since no "+" or "-" are present, the existing authorized users and
    # non-authorized CSCs will be replaced.
    AuthRequestData(
        cscs_to_command=f"Test:{INDEX1}, {NON_EXISTENT_CSC}, Test:{INDEX2}",
        authorized_users=", ".join(TEST_USERS_2),
        non_authorized_cscs=", ".join(TEST_CSCS_2),
        expected_authorized_users=[TEST_USERS_2, TEST_USERS_2],
        expected_non_authorized_cscs=[TEST_CSCS_2, TEST_CSCS_2],
        expected_failed_cscs={NON_EXISTENT_CSC},
    ),
    # Here we use a "+" for both the authorized users and the non-authorized
    # CSCs, meaning that they get added to the existing sets.
    AuthRequestData(
        cscs_to_command=f"Test:{INDEX1}, Test:{INDEX2}",
        authorized_users="+" + ", ".join(TEST_USERS_1),
        non_authorized_cscs="+" + ", ".join(TEST_CSCS_1),
        expected_authorized_users=[JOINED_TEST_USERS, JOINED_TEST_USERS],
        expected_non_authorized_cscs=[JOINED_TEST_CSCS, JOINED_TEST_CSCS],
        expected_failed_cscs=set(),
    ),
    # Here we use a "-" for both the authorized users and the non-authorized
    # CSCs, meaning that they get removed from the existing sets.
    AuthRequestData(
        cscs_to_command=f"Test:{INDEX1}, Test:{INDEX2}",
        authorized_users="-" + ", ".join(USERS_TO_REMOVE),
        non_authorized_cscs="-" + ", ".join(CSCS_TO_REMOVE),
        expected_authorized_users=[REMAINING_USERS, REMAINING_USERS],
        expected_non_authorized_cscs=[REMAINING_CSCS, REMAINING_CSCS],
        expected_failed_cscs=set(),
    ),
]


def create_rest_message_from_auth_request_data(
    ard: AuthRequestData, status: str
) -> RestMessageType:
    global message_id
    message_id = message_id + 1
    return asdict(
        RestMessage(
            id=message_id,
            cscs_to_change=ard.cscs_to_command,
            authorized_users=ard.authorized_users,
            unauthorized_cscs=ard.non_authorized_cscs,
            status=status,
        )
    )


def create_approved_rest_message_from_auth_request_data(
    ard: AuthRequestData,
) -> RestMessage:
    return create_rest_message_from_auth_request_data(ard, "Approved")


def create_pending_rest_message_from_auth_request_data(
    ard: AuthRequestData,
) -> RestMessage:
    return create_rest_message_from_auth_request_data(ard, "Pending")


# A list representing a single pending authorize request.
PENDING_AUTH_REQUESTS = [
    RestMessageData(
        rest_messages=[
            create_pending_rest_message_from_auth_request_data(TEST_DATA[0])
        ],
        expected_authorized_users=TEST_DATA[0].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[0].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[0].expected_failed_cscs,
    )
]

# A list of single and multiple approved authorization requests.
APPROVED_AUTH_REQUESTS = [
    RestMessageData(
        rest_messages=[
            create_approved_rest_message_from_auth_request_data(TEST_DATA[0]),
            create_approved_rest_message_from_auth_request_data(TEST_DATA[1]),
        ],
        expected_authorized_users=TEST_DATA[1].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[1].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[1].expected_failed_cscs,
    ),
    RestMessageData(
        rest_messages=[
            create_approved_rest_message_from_auth_request_data(TEST_DATA[2]),
        ],
        expected_authorized_users=TEST_DATA[2].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[2].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[2].expected_failed_cscs,
    ),
    RestMessageData(
        rest_messages=[
            create_approved_rest_message_from_auth_request_data(TEST_DATA[3]),
        ],
        expected_authorized_users=TEST_DATA[3].expected_authorized_users,
        expected_non_authorized_cscs=TEST_DATA[3].expected_non_authorized_cscs,
        expected_failed_cscs=TEST_DATA[3].expected_failed_cscs,
    ),
]
