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

    async def test_missing_forecast(self):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=2,
            config_dir=TEST_CONFIG_DIR,
        ):
            await self.remote.tel_hourlyTrend.aget(timeout=45)

    async def test_telemetry(self):
        test_file = pathlib.Path(
            "python/lsst/ts/weatherforecast/data/forecast-test.json"
        )
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=1,
            config_dir=TEST_CONFIG_DIR,
        ):
            metadata = await self.remote.tel_metadata.aget(timeout=45)
            assert approx(-30.24) == metadata.latitude
            assert approx(-70.34) == metadata.longitude
            assert 2298 == metadata.height
            assert "GMT-03" == metadata.timezoneAbbrevation
            assert -3 == metadata.timeOffset

            hourly_trend = await self.remote.tel_hourlyTrend.aget(timeout=10)
            daily_trend = await self.remote.tel_dailyTrend.aget(timeout=10)
            with open(test_file) as f:
                df = json.load(f)

            hourly_trend_fld = df["trend_1h"]
            for name, values in hourly_trend_fld.items():
                hourly_trend_fld[name] = values[:336]
            assert (
                approx(hourly_trend_fld["temperature"])
                == hourly_trend.temperature[:336]
            )
            assert (
                approx(hourly_trend_fld["temperature_spread"])
                == hourly_trend.temperatureSpread[:336]
            )
            assert (
                approx(hourly_trend_fld["precipitation"])
                == hourly_trend.precipitation[:336]
            )
            assert (
                approx(hourly_trend_fld["precipitation_spread"])
                == hourly_trend.precipitationSpread[:336]
            )
            assert approx(hourly_trend_fld["windspeed"]) == hourly_trend.windspeed[:336]
            assert (
                approx(hourly_trend_fld["windspeed_spread"])
                == hourly_trend.windspeedSpread[:336]
            )
            assert hourly_trend_fld["winddirection"] == hourly_trend.windDirection[:336]
            assert (
                hourly_trend_fld["sealevelpressure"]
                == hourly_trend.seaLevelPressure[:336]
            )
            assert (
                hourly_trend_fld["relativehumidity"]
                == hourly_trend.relativeHumidity[:336]
            )
            assert (
                approx(hourly_trend_fld["ghi_backwards"])
                == hourly_trend.ghiBackwards[:336]
            )
            assert (
                approx(hourly_trend_fld["extraterrestrialradiation_backwards"])
                == hourly_trend.extraTerrestrialRadiationBackwards[:336]
            )
            assert (
                hourly_trend_fld["totalcloudcover"]
                == hourly_trend.totalCloudCover[:336]
            )
            assert (
                hourly_trend_fld["totalcloudcover_spread"]
                == hourly_trend.totalCloudCoverSpread[:336]
            )
            assert (
                approx(hourly_trend_fld["snowfraction"])
                == hourly_trend.snowFraction[:336]
            )
            assert hourly_trend_fld["pictocode"] == hourly_trend.pictocode[:336]
            assert approx(hourly_trend_fld["gust"]) == hourly_trend.gust[:336]
            assert hourly_trend_fld["lowclouds"] == hourly_trend.lowClouds[:336]
            assert hourly_trend_fld["midclouds"] == hourly_trend.midClouds[:336]
            assert hourly_trend_fld["hiclouds"] == hourly_trend.highClouds[:336]
            assert hourly_trend_fld["sunshinetime"] == hourly_trend.sunshineTime[:336]
            assert hourly_trend_fld["visibility"] == hourly_trend.visibility[:336]
            assert (
                approx(hourly_trend_fld["skintemperature"])
                == hourly_trend.skinTemperature[:336]
            )
            assert (
                approx(hourly_trend_fld["dewpointtemperature"])
                == hourly_trend.dewPointTemperature[:336]
            )
            assert (
                hourly_trend_fld["precipitation_probability"]
                == hourly_trend.precipitationProbability[:336]
            )
            assert hourly_trend_fld["cape"] == hourly_trend.cape[:336]
            assert (
                approx(hourly_trend_fld["liftedindex"])
                == hourly_trend.liftedIndex[:336]
            )
            assert (
                approx(hourly_trend_fld["evapotranspiration"])
                == hourly_trend.evapoTranspiration[:336]
            )
            assert (
                approx(hourly_trend_fld["referenceevapotranspiration_fao"])
                == hourly_trend.referenceEvapoTranspirationFao[:336]
            )

            daily_trend_fld = df["trend_day"]
            for name, values in daily_trend_fld.items():
                daily_trend_fld[name] = values[:14]
            assert daily_trend_fld["pictocode"] == daily_trend.pictocode[:14]
            assert (
                approx(daily_trend_fld["temperature_max"])
                == daily_trend.temperatureMax[:14]
            )
            assert (
                approx(daily_trend_fld["temperature_min"])
                == daily_trend.temperatureMin[:14]
            )
            assert (
                approx(daily_trend_fld["temperature_mean"])
                == daily_trend.temperatureMean[:14]
            )
            assert (
                approx(daily_trend_fld["temperature_spread"])
                == daily_trend.temperatureSpread[:14]
            )
            assert daily_trend_fld["precipitation"] == daily_trend.precipitation[:14]
            assert (
                daily_trend_fld["precipitation_probability"]
                == daily_trend.precipitationProbability[:14]
            )
            assert (
                approx(daily_trend_fld["precipitation_spread"])
                == daily_trend.precipitationSpread[:14]
            )
            assert (
                approx(daily_trend_fld["windspeed_max"])
                == daily_trend.windspeedMax[:14]
            )
            assert (
                approx(daily_trend_fld["windspeed_min"])
                == daily_trend.windspeedMin[:14]
            )
            assert (
                approx(daily_trend_fld["windspeed_mean"])
                == daily_trend.windspeedMean[:14]
            )
            assert (
                approx(daily_trend_fld["windspeed_spread"])
                == daily_trend.windspeedSpread[:14]
            )
            assert daily_trend_fld["winddirection"] == daily_trend.windDirection[:14]
            assert (
                daily_trend_fld["sealevelpressure_max"]
                == daily_trend.seaLevelPressureMax[:14]
            )
            assert (
                daily_trend_fld["sealevelpressure_min"]
                == daily_trend.seaLevelPressureMin[:14]
            )
            assert (
                daily_trend_fld["sealevelpressure_mean"]
                == daily_trend.seaLevelPressureMean[:14]
            )
            assert (
                daily_trend_fld["relativehumidity_max"]
                == daily_trend.relativeHumidityMax[:14]
            )
            assert (
                daily_trend_fld["relativehumidity_min"]
                == daily_trend.relativeHumidityMin[:14]
            )
            assert (
                daily_trend_fld["relativehumidity_mean"]
                == daily_trend.relativeHumidityMean[:14]
            )
            assert (
                approx(daily_trend_fld["snowfraction"]) == daily_trend.snowFraction[:14]
            )
            assert daily_trend_fld["predictability"] == daily_trend.predictability[:14]
            assert (
                daily_trend_fld["predictability_class"]
                == daily_trend.predictabilityClass[:14]
            )
            assert (
                daily_trend_fld["totalcloudcover_max"]
                == daily_trend.totalCloudCoverMax[:14]
            )
            assert (
                daily_trend_fld["totalcloudcover_min"]
                == daily_trend.totalCloudCoverMin[:14]
            )
            assert (
                daily_trend_fld["totalcloudcover_mean"]
                == daily_trend.totalCloudCoverMean[:14]
            )
            assert (
                daily_trend_fld["totalcloudcover_spread"]
                == daily_trend.totalCloudCoverSpread[:14]
            )
            assert daily_trend_fld["ghi_total"] == daily_trend.ghiTotal[:14]
            assert (
                daily_trend_fld["extraterrestrialradiation_total"]
                == daily_trend.extraTerrestrialRadiationTotal[:14]
            )
            assert approx(daily_trend_fld["gust_max"]) == daily_trend.gustMax[:14]
            assert approx(daily_trend_fld["gust_min"]) == daily_trend.gustMin[:14]
            assert approx(daily_trend_fld["gust_mean"]) == daily_trend.gustMean[:14]
            assert daily_trend_fld["lowclouds_max"] == daily_trend.lowCloudsMax[:14]
            assert daily_trend_fld["lowclouds_min"] == daily_trend.lowCloudsMin[:14]
            assert daily_trend_fld["lowclouds_mean"] == daily_trend.lowCloudsMean[:14]
            assert daily_trend_fld["midclouds_max"] == daily_trend.midCloudsMax[:14]
            assert daily_trend_fld["midclouds_min"] == daily_trend.midCloudsMin[:14]
            assert daily_trend_fld["midclouds_mean"] == daily_trend.midCloudsMean[:14]
            assert daily_trend_fld["hiclouds_max"] == daily_trend.hiCloudsMax[:14]
            assert daily_trend_fld["hiclouds_min"] == daily_trend.hiCloudsMin[:14]
            assert daily_trend_fld["hiclouds_mean"] == daily_trend.hiCloudsMean[:14]
            assert daily_trend_fld["sunshinetime"] == daily_trend.sunshineTime[:14]
            assert daily_trend_fld["visibility_max"] == daily_trend.visibilityMax[:14]
            assert daily_trend_fld["visibility_min"] == daily_trend.visibilityMin[:14]
            assert daily_trend_fld["visibility_mean"] == daily_trend.visibilityMean[:14]
            assert (
                approx(daily_trend_fld["skintemperature_max"])
                == daily_trend.skinTemperatureMax[:14]
            )
            assert (
                approx(daily_trend_fld["skintemperature_min"])
                == daily_trend.skinTemperatureMin[:14]
            )
            assert (
                approx(daily_trend_fld["skintemperature_mean"])
                == daily_trend.skinTemperatureMean[:14]
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_max"])
                == daily_trend.dewPointTemperatureMax[:14]
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_min"])
                == daily_trend.dewPointTemperatureMin[:14]
            )
            assert (
                approx(daily_trend_fld["dewpointtemperature_mean"])
                == daily_trend.dewPointTemperatureMean[:14]
            )
            assert daily_trend_fld["cape_max"] == daily_trend.capeMax[:14]
            assert daily_trend_fld["cape_min"] == daily_trend.capeMin[:14]
            assert daily_trend_fld["cape_mean"] == daily_trend.capeMean[:14]
            assert (
                approx(daily_trend_fld["liftedindex_max"])
                == daily_trend.liftedIndexMax[:14]
            )
            assert (
                approx(daily_trend_fld["liftedindex_min"])
                == daily_trend.liftedIndexMin[:14]
            )
            assert (
                approx(daily_trend_fld["liftedindex_mean"])
                == daily_trend.liftedIndexMean[:14]
            )
            assert (
                approx(daily_trend_fld["evapotranspiration"])
                == daily_trend.evapoTranspiration[:14]
            )
            assert (
                approx(daily_trend_fld["referenceevapotranspiration_fao"])
                == daily_trend.referenceEvapoTranspirationFao[:14]
            )
