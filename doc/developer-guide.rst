.. py:currentmodule:: lsst.ts.authorize

.. _lsst.ts.authorize.developer_guide:

###############
Developer Guide
###############

The authorize CSC is implemented using `ts_salobj <https://github.com/lsst-ts/ts_salobj>`_.

.. _lsst.ts.authorize-api:

API
===

The primary class is `Authorize`: the CSC.

.. automodapi:: lsst.ts.authorize
   :no-main-docstr:

.. _lsst.ts.authorize-build_and_test:

Build and Test
==============

This is a pure python package.
There is nothing to build except the documentation.

.. code-block:: bash

    make_idl_files.py Authorize  # plus any CSCs for which you want to set authorization
    setup -r .
    pytest -v  # to run tests
    package-docs clean; package-docs build  # to build the documentation

.. _lsst.ts.authorize-contributing:

Contributing
============

``lsst.ts.authorize`` is developed at https://github.com/lsst-ts/ts_authorize.
You can find Jira issues for this module using `labels=ts_authorize <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20ts_authorize>`_.
