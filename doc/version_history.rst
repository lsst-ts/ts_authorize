.. py:currentmodule:: lsst.ts.authorize

.. _lsst.ts.authorize.version_history:

###############
Version History
###############

v0.6.12
-------

* Update the version of ts-conda-build to 0.4 in the conda recipe.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.11
-------

* Use ts_xml instead of ts_idl for getting a list of all TSSW components.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.10
-------

* Improve error message.
* Remove for loop.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.9
------

* Better handle errors in the authorize request data.
  This means that validation errors get caught and processed.
  The CSC now keeps on accepting commands in case of auto authorization and it keeps on polling the REST server in case of non-auto authorization.
* Verify the CSC names against the list of subsystems in ts_xml.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.8
------

* Add debug statements and better error handling.
* Update Jenkinsfile to use DevelopPipeline.
* Switch to using ts-pre-commit-config.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.7
------

* Update the code that handles the authentication response.
* Make sure that the CSC goes to FAULT state in case of an error in the RestAuthorizeHandler.
* Handle the POST response code 201 correctly.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.6
------

* Make sure that only one ClientSession is used when communicating with the REST server.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.5
------

* Fix wrong docstring formatting.
* Code improvements related to review comments.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.4
------

* Add authentication to the RestAuthorizeHandler.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.3
------

* Clean up conda recipe.
* Fix LOVE REST API URL.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.2
------

* pre-commit: update mypy version

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.1
------
* Fix conda deployment dependencies.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.6.0
------
* Sort imports with isort.
* Add full MyPy support.
* Modernize the pre-commit hooks.
* Extract auto authorize code to separate class.
* Store success and failure info in instance variables for further processing.
* Add a test utility for testing multiple scenarios.
* Add support for the LOVE REST API.
  The CSC polls the REST server on a regular basis and processes approved but unprocessed authorize requests.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.5.0
------

* Rename command-line scripts to remove ".py" suffix.
* Build with pyproject.toml.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.4.2
------

* Overhaul the documentation.
* `CONFIG_SCHEMA`: remove a few remaining default values.
* ``setup.cfg``: add ``asyncio_mode = auto``.
* ``.pre-commit-config.yaml``: update software versions.

Requirements:

* ts_salobj 7
* IDL files for Authorize, plus all subsystems to authorize, built with ts_xml 11

v0.4.1
------

* Update conda jenkins build script.
* Update setup.py
* Update conda recipe.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.4.0
------

* Update for ts_salobj v7, which is required.
  This also requires ts_xml 11.
* Jenkinsfile: update to pull the current salobj.

Requirements:

* ts_salobj 7
* IDL files for Authorize plus all subsystems to authorize, built with ts_xml 11

v0.3.0
------

* Convert Authorize to a CSC full featured configurable CSC and prepare it to interface with LOVE.

Requirements:

* ts_salobj >6
* ts_xml >10.1
* IDL files for Authorize plus all subsystems to authorize.

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
* IDL files for Authorize plus all subsystems to authorize, generated by ts_sal 4.2 or later

v0.2.0
------

* Add setup.py and conda build files.

Requirements:

* ts_salobj 6
* ts_xml 6
* IDL files for Authorize plus all subsystems to authorize, generated by ts_sal 4.2 or later

v0.1.0
------

* Initial release

Requirements:

* ts_salobj 6
* ts_xml 6
* IDL files for Authorize plus all subsystems to authorize, generated by ts_sal 4.2 or later
