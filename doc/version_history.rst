.. _version_history:Version_History:

===============
Version History
===============

.. towncrier release notes start

v0.7.0 (2026-10-07)
===================

New Features
------------

- Added new source of temperature that is generated from prophet forecast data model. (`OSW-846 <https://rubinobs.atlassian.net//browse/OSW-846>`_)
- Added disable_meteoblue flag. (`OSW-1531 <https://rubinobs.atlassian.net//browse/OSW-1531>`_)


Bug Fixes
---------

- Set None values to math.nan for every field before publishing. (`OSW-929 <https://rubinobs.atlassian.net//browse/OSW-929>`_)
- Fixed query call to use right prefix. (`OSW-1802 <https://rubinobs.atlassian.net//browse/OSW-1802>`_)
- Changed field to use yhat instead of trend. (`OSW-1802 <https://rubinobs.atlassian.net//browse/OSW-1802>`_)
- Fixed get_prediction_loop by calling get_prediction method and ensuring that the value is a list. (`OSW-1858 <https://rubinobs.atlassian.net//browse/OSW-1858>`_)
- Fixed error by removing duplicate index from EFD client. (`OSW-1858 <https://rubinobs.atlassian.net//browse/OSW-1858>`_)
- Go to fault state if prophet prediction fails. (`OSW-1858 <https://rubinobs.atlassian.net//browse/OSW-1858>`_)
- Changed base to use base_efd instead of summit_efd_copy. (`OSW-2149 <https://rubinobs.atlassian.net//browse/OSW-2149>`_)
- Changed calls to be model.fit and model.predict in module not in prophet library. (`OSW-2149 <https://rubinobs.atlassian.net//browse/OSW-2149>`_)
- Fixed SITE to be LSST_SITE. (`OSW-2149 <https://rubinobs.atlassian.net//browse/OSW-2149>`_)
- Updated efd client to v1.


Performance Enhancement
-----------------------

- Reduced telemetry loop complexity. (`OSW-846 <https://rubinobs.atlassian.net//browse/OSW-846>`_)
- Added try-except handling to get_prediction_loop. (`OSW-1858 <https://rubinobs.atlassian.net//browse/OSW-1858>`_)


Other Changes and Additions
---------------------------

- Added python version to build string for conda package. (`OSW-1484 <https://rubinobs.atlassian.net//browse/OSW-1484>`_)
- Pinned prophet to 1.2 in conda recipe. (`OSW-1715 <https://rubinobs.atlassian.net//browse/OSW-1715>`_)


v0.6.1 (2025-08-25)
===================

Bug Fixes
---------

- Added timezone awareness to timestamp conversion. (`OSW-675 <https://rubinobs.atlassian.net//browse/OSW-675>`_)


v0.6.0 (2025-05-16)
===================

New Features
------------

- Added Above Sea Level to API call to improve accuracy. (`DM-50711 <https://rubinobs.atlassian.net//browse/DM-50711>`_)


Performance Enhancement
-----------------------

- Changed longitude to use Google Maps location for Cerro Pachon. (`DM-50711 <https://rubinobs.atlassian.net//browse/DM-50711>`_)


Other Changes and Additions
---------------------------

- Added mypy and ruff support. (`DM-50711 <https://rubinobs.atlassian.net//browse/DM-50711>`_)


ts_weatherforecast v0.5.0 (2025-04-23)
======================================

Features
--------

- Changed interval to update forecast at 4am and 4pm. (`DM-47997 <https://rubinobs.atlassian.net/DM-47997>`_)


Bugfixes
--------

- Update ts-conda-build to 0.4. (`DM-43486 <https://rubinobs.atlassian.net/DM-43486>`_)
- Go to fault state when retry exceeds max retries. (`DM-47997 <https://rubinobs.atlassian.net/DM-47997>`_)


ts_weatherforecast v0.4.0 (2024-03-14)
======================================

Features
--------

- Change hiclouds to highclouds in meteoblue API. (`DM-43292 <https://jira.lsstcorp.org/DM-43292>`_)


Bugfixes
--------

- Correct modelrun and modelrunUpdateTime to be strings instead of floats. (`DM-43292 <https://jira.lsstcorp.org/DM-43292>`_)


Improved Documentation
----------------------

- Add towncrier support. (`DM-43292 <https://jira.lsstcorp.org/DM-43292>`_)


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
