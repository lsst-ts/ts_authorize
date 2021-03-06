.. py:currentmodule:: lsst.ts.authorize

.. _lsst.ts.authorize.version_history:

###############
Version History
###############

v0.2.1
------

* Use `unittest.IsolatedAsyncioTestCase` instead of the abandoned asynctest package.
* Use pre-commit instead of a custom pre-commit hook; see the README.md for instructions.
* Format the code with black 20.8b1.
* Modernize the code to eliminate several warnings.
* Modernize doc/conf.py for documenteer 0.6.

Requirements:

* ts_salobj 6
* ts_xml 6
* IDL file for Authorize generated by ts_sal 4.2 or later

v0.2.0
------

* Add setup.py and conda build files.

Requirements:

* ts_salobj 6
* ts_xml 6
* IDL file for Authorize generated by ts_sal 4.2 or later

v0.1.0
------

* Initial release

Requirements:

* ts_salobj 6
* ts_xml 6
* IDL file for Authorize generated by ts_sal 4.2 or later
