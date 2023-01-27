# This file is part of ts_weatherforecast.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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

import json
import os
import pathlib
import unittest

from lsst.ts import salobj, weatherforecast
from pytest import approx

TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class WeatherForecastCSCTestCase(
    salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase
):
    """Run WeatherForecastCSC test case."""

    def setUp(self):
        """Setup the test with LSST_SITE environment value"""
        os.environ["LSST_SITE"] = "weatherforecast"
        os.environ["METEOBLUE_API_KEY"] = "test"
        return super().setUp()

    def basic_make_csc(
        self, initial_state, config_dir=TEST_CONFIG_DIR, simulation_mode=1, **kwargs
    ):
        return weatherforecast.csc.WeatherForecastCSC(
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_dir=config_dir,
        )

    async def test_bin_script(self):
        await self.check_bin_script(
            name="WeatherForecast", index=False, exe_name="run_weatherforecast"
        )

    async def test_telemetry(self):
        test_file = pathlib.Path(
            "python/lsst/ts/weatherforecast/data/forecast-test.json"
        )
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            metadata = await self.remote.tel_metadata.aget(timeout=10)
            assert approx(-30.24) == metadata.latitude
            assert approx(-70.34) == metadata.longitude
            assert 2298 == metadata.height
            assert "GMT-03" == metadata.timezoneAbbrevation
            assert -3 == metadata.timeOffset

            hourly_trend = await self.remote.tel_hourlyTrend.aget()
            daily_trend = await self.remote.tel_dailyTrend.aget()
            with open(test_file) as f:
                df = json.load(f)

            hourly_trend_fld = df["trend_1h"]
            assert approx(hourly_trend_fld["temperature"]) == hourly_trend.temperature
            assert (
                approx(hourly_trend_fld["temperature_spread"])
                == hourly_trend.temperatureSpread
            )
            assert (
                approx(hourly_trend_fld["precipitation"]) == hourly_trend.precipitation
            )
            assert (
                approx(hourly_trend_fld["precipitation_spread"])
                == hourly_trend.precipitationSpread
            )
            assert approx(hourly_trend_fld["windspeed"]) == hourly_trend.windspeed
            assert (
                approx(hourly_trend_fld["windspeed_spread"])
                == hourly_trend.windspeedSpread
            )
            assert hourly_trend_fld["winddirection"] == hourly_trend.windDirection
            assert hourly_trend_fld["sealevelpressure"] == hourly_trend.seaLevelPressure
            assert hourly_trend_fld["relativehumidity"] == hourly_trend.relativeHumidity
            assert (
                approx(hourly_trend_fld["ghi_backwards"]) == hourly_trend.ghiBackwards
            )
            assert (
                approx(hourly_trend_fld["extraterrestrialradiation_backwards"])
                == hourly_trend.extraTerrestrialRadiationBackwards
            )
            assert hourly_trend_fld["totalcloudcover"] == hourly_trend.totalCloudCover
            assert (
                hourly_trend_fld["totalcloudcover_spread"]
                == hourly_trend.totalCloudCoverSpread
            )
            assert approx(hourly_trend_fld["snowfraction"]) == hourly_trend.snowFraction
            assert hourly_trend_fld["pictocode"] == hourly_trend.pictocode
            assert approx(hourly_trend_fld["gust"]) == hourly_trend.gust
            assert hourly_trend_fld["lowclouds"] == hourly_trend.lowClouds
            assert hourly_trend_fld["midclouds"] == hourly_trend.midClouds
            assert hourly_trend_fld["hiclouds"] == hourly_trend.highClouds
            assert hourly_trend_fld["sunshinetime"] == hourly_trend.sunshineTime
            assert hourly_trend_fld["visibility"] == hourly_trend.visibility
            assert (
                approx(hourly_trend_fld["skintemperature"])
                == hourly_trend.skinTemperature
            )
            assert (
                approx(hourly_trend_fld["dewpointtemperature"])
                == hourly_trend.dewPointTemperature
            )
            assert (
                hourly_trend_fld["precipitation_probability"]
                == hourly_trend.precipitationProbability
            )
            assert hourly_trend_fld["cape"] == hourly_trend.cape
            assert approx(hourly_trend_fld["liftedindex"]) == hourly_trend.liftedIndex
            assert (
                approx(hourly_trend_fld["evapotranspiration"])
                == hourly_trend.evapoTranspiration
            )
            assert (
                approx(hourly_trend_fld["referenceevapotranspiration_fao"])
                == hourly_trend.referenceEvapoTranspirationFao
            )

            daily_trend_fld = df["trend_day"]
            assert daily_trend_fld["pictocode"] == daily_trend.pictocode
            assert (
                approx(daily_trend_fld["temperature_max"]) == daily_trend.temperatureMax
            )
            assert (
                approx(daily_trend_fld["temperature_min"]) == daily_trend.temperatureMin
            )
            assert (
                approx(daily_trend_fld["temperature_mean"])
                == daily_trend.temperatureMean
            )
            assert (
                approx(daily_trend_fld["temperature_spread"])
                == daily_trend.temperatureSpread
            )
            assert daily_trend_fld["precipitation"] == daily_trend.precipitation
            assert (
                daily_trend_fld["precipitation_probability"]
                == daily_trend.precipitationProbability
            )
            assert (
                approx(daily_trend_fld["precipitation_spread"])
                == daily_trend.precipitationSpread
            )
            assert approx(daily_trend_fld["windspeed_max"]) == daily_trend.windspeedMax
            assert approx(daily_trend_fld["windspeed_min"]) == daily_trend.windspeedMin
            assert (
                approx(daily_trend_fld["windspeed_mean"]) == daily_trend.windspeedMean
            )
            assert (
                approx(daily_trend_fld["windspeed_spread"])
                == daily_trend.windspeedSpread
            )
            assert daily_trend_fld["winddirection"] == daily_trend.windDirection
            assert (
                daily_trend_fld["sealevelpressure_max"]
                == daily_trend.seaLevelPressureMax
            )
            assert (
                daily_trend_fld["sealevelpressure_min"]
                == daily_trend.seaLevelPressureMin
            )
            assert (
                daily_trend_fld["sealevelpressure_mean"]
                == daily_trend.seaLevelPressureMean
            )
            assert (
                daily_trend_fld["relativehumidity_max"]
                == daily_trend.relativeHumidityMax
            )
            assert (
                daily_trend_fld["relativehumidity_min"]
                == daily_trend.relativeHumidityMin
            )
            assert (
                daily_trend_fld["relativehumidity_mean"]
                == daily_trend.relativeHumidityMean
            )
            assert approx(daily_trend_fld["snowfraction"]) == daily_trend.snowFraction
            assert daily_trend_fld["predictability"] == daily_trend.predictability
            assert (
                daily_trend_fld["predictability_class"]
                == daily_trend.predictabilityClass
            )
            assert (
                daily_trend_fld["totalcloudcover_max"] == daily_trend.totalCloudCoverMax
            )
            assert (
                daily_trend_fld["totalcloudcover_min"] == daily_trend.totalCloudCoverMin
            )
            assert (
                daily_trend_fld["totalcloudcover_mean"]
                == daily_trend.totalCloudCoverMean
            )
            assert (
                daily_trend_fld["totalcloudcover_spread"]
                == daily_trend.totalCloudCoverSpread
            )
            assert daily_trend_fld["ghi_total"] == daily_trend.ghiTotal
            assert (
                daily_trend_fld["extraterrestrialradiation_total"]
                == daily_trend.extraTerrestrialRadiationTotal
            )
            assert approx(daily_trend_fld["gust_max"]) == daily_trend.gustMax
            assert approx(daily_trend_fld["gust_min"]) == daily_trend.gustMin
            assert approx(daily_trend_fld["gust_mean"]) == daily_trend.gustMean
            assert daily_trend_fld["lowclouds_max"] == daily_trend.lowCloudsMax
            assert daily_trend_fld["lowclouds_min"] == daily_trend.lowCloudsMin
            assert daily_trend_fld["lowclouds_mean"] == daily_trend.lowCloudsMean
            assert daily_trend_fld["midclouds_max"] == daily_trend.midCloudsMax
            assert daily_trend_fld["midclouds_min"] == daily_trend.midCloudsMin
            assert daily_trend_fld["midclouds_mean"] == daily_trend.midCloudsMean
            assert daily_trend_fld["hiclouds_max"] == daily_trend.hiCloudsMax
            assert daily_trend_fld["hiclouds_min"] == daily_trend.hiCloudsMin
            assert daily_trend_fld["hiclouds_mean"] == daily_trend.hiCloudsMean
            assert daily_trend_fld["sunshinetime"] == daily_trend.sunshineTime
            assert daily_trend_fld["visibility_max"] == daily_trend.visibilityMax
            assert daily_trend_fld["visibility_min"] == daily_trend.visibilityMin
            assert daily_trend_fld["visibility_mean"] == daily_trend.visibilityMean
            assert (
                approx(daily_trend_fld["skintemperature_max"])
                == daily_trend.skinTemperatureMax
            )
            assert (
                approx(daily_trend_fld["skintemperature_min"])
                == daily_trend.skinTemperatureMin
            )
            assert (
                approx(daily_trend_fld["skintemperature_mean"])
                == daily_trend.skinTemperatureMean
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_max"])
                == daily_trend.dewPointTemperatureMax
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_min"])
                == daily_trend.dewPointTemperatureMin
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_mean"])
                == daily_trend.dewPointTemperatureMean
            )
            assert daily_trend_fld["cape_max"] == daily_trend.capeMax
            assert daily_trend_fld["cape_min"] == daily_trend.capeMin
            assert daily_trend_fld["cape_mean"] == daily_trend.capeMean
            assert (
                approx(daily_trend_fld["liftedindex_max"]) == daily_trend.liftedIndexMax
            )
            assert (
                approx(daily_trend_fld["liftedindex_min"]) == daily_trend.liftedIndexMin
            )
            assert (
                approx(daily_trend_fld["liftedindex_mean"])
                == daily_trend.liftedIndexMean
            )
            assert (
                approx(daily_trend_fld["evapotranspiration"])
                == daily_trend.evapoTranspiration
            )
            assert (
                approx(daily_trend_fld["referenceevapotranspiration_fao"])
                == daily_trend.referenceEvapoTranspirationFao
            )
