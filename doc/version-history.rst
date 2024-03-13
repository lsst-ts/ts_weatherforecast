.. _version_history:Version_History:

===============
Version History
===============

.. towncrier release notes start

v0.3.3
======
* Pin aiohttp to above or equal to 3.8.

v0.3.2
======
* Remove api key from log.
* Remove unnecessary log messages for fixing data length.
* Add workaround to truncate data to 336 and 14 for hourly and daily trends.
* Use DevelopPipeline.
* Use generate_pre_commit_conf.
* Remove workaround
* Cleanup log messages

v0.3.1
======
* Add count check to trend_daily and hourly fields.
* Attempt to pad or equalize data when count is mismatched.
* Add simulation mode that has missing data.

v0.3.0
======
* Make CSC configurable.

v0.2.0
======
* Add MockServer.
* Fix SITE_URL constant.
* Make enable_cmdline_state true.
* Check if extraTerrestrialRadiationBackwards contains None and clean it.
* Make sure that telemetry_loop is in a while loop.
* If bad request is received, wait an amount of time to try again.

v0.1.4
======
* Add missing execute_csc function to csc module
* Add missing bin folder and run_weatherforecast script

v0.1.3
======

* Correct the conda package name.

Requires:

* ts_salobj 7.0
* ts_idl 3.1
* ts_utils 1.0
* IDL files for WeatherForecast from ts_xml 13.0

v0.1.2
======

* Fix the conda build again.

Requires:

* ts_salobj 7.0
* ts_idl 3.1
* ts_utils 1.0
* IDL files for WeatherForecast from ts_xml 13.0

v0.1.1
======

* Fix the conda build.

Requires:

* ts_salobj 7.0
* ts_idl 3.1
* ts_utils 1.0
* IDL files for WeatherForecast from ts_xml 13.0

v0.1.0
======

* Inital release
