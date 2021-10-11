# This file is part of ts_love_csc.
#
# Developed for Rubin Observatory Telescope and Site Systems.
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

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_love_csc/blob/master/python/lsst/ts/love/csc/config_schema.py
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: LOVE v1
description: Schema for LOVE configuration files
type: object
properties:
    host:
        type: string
        description: >-
            Hostname of the LOVE server to validate request authorization
            commands.
    port:
        type: integer
        description: Port to connect to the LOVE server (see host for more information).
    timeout_request_authorization:
        type: number
        description: >-
            Timeout for waiting requests to change the authlist to be processed
            by operators.
        default: 60.
    auto_authorization:
        type: boolean
        description: >-
            Automatically aprove authorization requests? If true (default) all
            requests are approved automatically. If false, a request to the
            LOVE frontend is generated.
        default: true
additionalProperties: false
"""
)
