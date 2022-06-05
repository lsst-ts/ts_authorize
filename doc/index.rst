.. py:currentmodule:: lsst.ts.authorize

.. _lsst.ts.authorize:

#################
lsst.ts.authorize
#################

.. image:: https://img.shields.io/badge/Project Metadata-gray.svg
    :target: https://ts-xml.lsst.io/index.html#index-csc-table-authorize
.. image:: https://img.shields.io/badge/SAL\ Interface-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/Authorize.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_authorize
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_authorize

Overview
========

A CSC that manages the authorization lists for CSCs.

Authorization lists control who can control a CSC, to reduce the danger of people from interfering with each other.
Authorization lists are cooperative; they only work if everybody plays by the rules.

.. warning:: **authorization lists are not safe**; they provide **no protection of people or equipment!**.

The Authorize CSC manages requests to authorize users or unauthorize CSCs.
For now all authorization requests are granted.
A future update of the CSC will send authorization requests to the LOVE system for operator approval.

.. _lsst.ts.authorize-user_guide:

User Guide
==========

Start the authorization CSC using command-line script `run_authorization_service`.
It takes no arguments.

There are two ways to request authorization:

* Use the command-line script `request_authorization`.
  Run with ``--help`` for details.

* Issue the `requestAuthorization command <https://ts-xml.lsst.io/sal_interfaces/Authorize.html#requestauthorization>`_.

Configuration
-------------

Configuration specifies parameters for the connection to LOVE, which is not yet implemented.
Configuration is defined by `CONFIG_SCHEMA <https://github.com/lsst-ts/ts_authorize/blob/develop/python/lsst/ts/authorize/config_schema.py>`_.
Configuration files live in `ts_config_ocs/Authorize <https://github.com/lsst-ts/ts_config_ocs/tree/develop/Authorize>`_.

Developer Guide
===============

.. toctree::
    developer-guide
    :maxdepth: 1

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
