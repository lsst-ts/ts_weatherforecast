import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_weatherforecast/blob/main/python/lsst/ts/weatherforecast/config_schema.py
title: WeatherForecast v1
description: Schema for WeatherForecast configuration files
type: object
additionalProperties: false
properties:
    tel_loop_error_wait_time:
        description: How long to wait to retry when API calls fails
        type: number
"""
)
