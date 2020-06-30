.. py:currentmodule:: lsst.ts.authorize

.. _lsst.ts.authorize:

#################
lsst.ts.authorize
#################

A service to handle requests for changes to the authorization list in one or more CSCs.

.. _lsst.ts.authorize-using:

Using lsst.ts.authorize
=======================

Run the authorization service using command-line script `run_authorization_service.py`.
It takes no arguments.

Issue requests for authorization using command-line script `request_authorization.py`.
Run with ``--help`` for details.

.. _lsst.ts.authorize-contributing:

Contributing
============

``lsst.ts.authorize`` is developed at https://github.com/lsst-ts/ts_authorize.
You can find Jira issues for this module using `labels=ts_authorize <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20ts_authorize>`_.

Python API reference
====================

.. automodapi:: lsst.ts.authorize
   :no-main-docstr:

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
