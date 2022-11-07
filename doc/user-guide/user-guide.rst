..
  This is a template for the user-guide documentation that will accompany each CSC.
  This template is provided to ensure that the documentation remains similar in look, feel, and contents to users.
  The headings below are expected to be present for all CSCs, but for many CSCs, additional fields will be required.

  ** All text in square brackets [] must be re-populated accordingly **

  See https://developer.lsst.io/restructuredtext/style.html
  for a guide to reStructuredText writing.

  Use the following syntax for sections:

  Sections
  ========

  and

  Subsections
  -----------

  and

  Subsubsections
  ^^^^^^^^^^^^^^

  To add images, add the image file (png, svg or jpeg preferred) to the
  images/ directory. The reST syntax for adding the image is

  .. figure:: /images/filename.ext
   :name: fig-label

   Caption text.

  Feel free to delete this instructional comment.

.. Fill out data so contacts section below is auto-populated
.. add name and email between the *'s below e.g. *Marie Smith <msmith@lsst.org>*
.. |CSC_developer| replace::  *Replace-with-name-and-email*
.. |CSC_product_owner| replace:: *Replace-with-name-and-email*

.. _User_Guide:

#######################
WeatherForecast User Guide
#######################


The WeatherForecast CSC provides forecast information for telescope operations by using Meteoblue Forecast API.

WeatherForecast Interface
======================

There are only 3 telemetry topics 

* metadata - contains metadata about the forecast model such as location, elevation and time updated
* trendHourly - contains data regarding each hour of the forecast
* trendDaily - contains data regarding each day of the forecast

Example Use-Case
================

.. code::

    metadata = await weatherforecast.tel_metadata.aget()
    
