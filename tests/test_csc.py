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

import datetime
import json
import os
import pathlib
import re
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
            await self.assert_next_sample(topic=self.remote.tel_hourlyTrend)

    async def test_bad_request(self):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=3,
            config_dir=TEST_CONFIG_DIR,
        ):
            await self.assert_next_summary_state(state=salobj.State.FAULT, flush=True)

    def check_arrays(self, response, expected, length):
        missing_names = []
        for name, values in vars(response).items():
            name2 = name.lower()
            name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            if name in expected:
                assert values[:length] == approx(expected[name][:length])
            elif name == "timestamp":
                converted_timestamps = [
                    datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M").timestamp()
                    for timestamp in expected["time"]
                ]
                assert values[:length] == approx(converted_timestamps[:length])
            elif name.startswith("private"):
                pass
            elif name2 in expected:
                assert values[:length] == approx(expected[name2][:length])
            elif name == "extra_terrestrial_radiation_backwards":
                assert values[:length] == approx(
                    expected["extraterrestrialradiation_backwards"][:length]
                )
            elif name == "total_cloud_cover_spread":
                assert values[:length] == approx(
                    expected["totalcloudcover_spread"][:length]
                )
            elif name == "high_clouds":
                assert values[:length] == approx(expected["hiclouds"][:length])
            elif name == "reference_evapo_transpiration_fao":
                assert values[:length] == approx(
                    expected["referenceevapotranspiration_fao"][:length]
                )
            else:
                missing_names.append(name)

    async def test_telemetry(self):
        test_file = pathlib.Path(
            "python/lsst/ts/weatherforecast/data/forecast-test.json"
        )
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=1,
            config_dir=TEST_CONFIG_DIR,
        ):
            metadata = await self.assert_next_sample(topic=self.remote.tel_metadata)
            assert approx(-30.24) == metadata.latitude
            assert approx(-70.34) == metadata.longitude
            assert 2298 == metadata.height
            assert "GMT-03" == metadata.timezoneAbbrevation
            assert -3 == metadata.timeOffset

            hourly_trend = await self.assert_next_sample(
                topic=self.remote.tel_hourlyTrend
            )
            daily_trend = await self.assert_next_sample(
                topic=self.remote.tel_dailyTrend
            )
            with open(test_file) as f:
                df = json.load(f)

            hourly_trend_fld = df["trend_1h"]
            self.check_arrays(
                hourly_trend,
                hourly_trend_fld,
                weatherforecast.GUARANTEED_HOURLY_TREND_LENGTH,
            )

            daily_trend_fld = df["trend_day"]
            self.check_arrays(
                daily_trend,
                daily_trend_fld,
                weatherforecast.GUARANTEED_DAILY_TREND_LENGTH,
            )
