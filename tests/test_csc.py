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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import datetime
import json
import math
import os
import pathlib
import re
import types
import typing
import unittest
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from pytest import approx

from lsst.ts import salobj, weatherforecast

TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")
TIMEOUT = 150


class CurveTestCase(unittest.TestCase):
    """Validate service curves without starting a CSC or Kafka."""

    def test_curve_validation(self) -> None:
        csc = weatherforecast.csc.WeatherForecastCSC
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        rows = [
            {
                "time": (start + datetime.timedelta(minutes=30 * index)).isoformat(),
                "temperature": float(index),
            }
            for index in range(26)
        ]
        assert csc.parse_curve({"curve": rows}) == [
            (start.timestamp() + 1800 * index, float(index)) for index in range(26)
        ]
        invalid: dict[str, typing.Any]
        for invalid in (
            {"curve": []},
            {"curve": rows[:-1]},
            {"curve": rows + [rows[-1]]},
            {"curve": "invalid"},
            {"curve": list(reversed(rows))},
            {"curve": [rows[0]] + rows[:-1]},
            {"curve": rows[:-1] + [{"time": rows[-1]["time"], "temperature": "nan"}]},
            {"curve": rows[:-1] + [{"time": rows[-1]["time"], "temperature": "inf"}]},
            {"curve": rows[:-1] + [{"time": rows[-1]["time"], "temperature": "invalid"}]},
            {"curve": rows[:-1] + [{"time": "2026-01-01T12:30:00", "temperature": 25.0}]},
            {"curve": rows[:-1] + [{"time": "invalid", "temperature": 25.0}]},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                csc.parse_curve(invalid)
        for invalid in (
            {},
            {"curve": rows[:-1] + [{"temperature": 25.0}]},
            {"curve": rows[:-1] + [{"time": rows[-1]["time"]}]},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(KeyError):
                csc.parse_curve(invalid)


class PredictionLoopTestCase(unittest.IsolatedAsyncioTestCase):
    """Check publication with both old and new XML interfaces."""

    async def test_optional_nbeats_topic(self) -> None:
        curve = [(float(index * 1800), float(index)) for index in range(26)]
        for has_topic in (False, True):
            with self.subTest(has_topic=has_topic):
                csc = types.SimpleNamespace(
                    make_prediction=AsyncMock(return_value=curve),
                    fault=AsyncMock(),
                )
                topic = types.SimpleNamespace(set_write=AsyncMock())
                if has_topic:
                    csc.tel_nbeats = topic
                with patch(
                    "lsst.ts.weatherforecast.csc.asyncio.sleep",
                    side_effect=asyncio.CancelledError,
                ) as sleep:
                    with self.assertRaises(asyncio.CancelledError):
                        await weatherforecast.csc.WeatherForecastCSC.prediction_loop(csc)
                csc.make_prediction.assert_awaited_once()
                csc.fault.assert_not_awaited()
                sleep.assert_awaited_once_with(60 * 15)
                if has_topic:
                    topic.set_write.assert_awaited_once_with(
                        timestamp=[point[0] for point in curve],
                        temperature=[point[1] for point in curve],
                    )
                else:
                    topic.set_write.assert_not_awaited()


class WeatherForecastCSCTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    """Run WeatherForecastCSC test case."""

    def setUp(self) -> None:
        """Setup the test with LSST_SITE environment value"""
        os.environ["LSST_SITE"] = "weatherforecast"
        os.environ["METEOBLUE_API_KEY"] = "test"
        return super().setUp()

    def basic_make_csc(
        self,
        initial_state: salobj.State,
        config_dir: pathlib.Path = TEST_CONFIG_DIR,
        simulation_mode: int = 1,
        **kwargs: typing.Any,
    ) -> weatherforecast.csc.WeatherForecastCSC:
        return weatherforecast.csc.WeatherForecastCSC(
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_dir=config_dir,
            override=kwargs.get("override", ""),
        )

    async def test_bin_script(self) -> None:
        await self.check_bin_script(name="WeatherForecast", index=False, exe_name="run_weatherforecast")

    async def test_missing_forecast(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=2,
            config_dir=TEST_CONFIG_DIR,
        ):
            await self.assert_next_sample(topic=self.remote.tel_hourlyTrend)

    async def test_bad_request(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=3,
            config_dir=TEST_CONFIG_DIR,
        ):
            await self.assert_next_summary_state(state=salobj.State.ENABLED)
            await self.assert_next_summary_state(state=salobj.State.FAULT, timeout=TIMEOUT)

    async def test_prediction_exception_faults_csc(self) -> None:
        async def fail_prediction(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            raise RuntimeError("prediction failed")

        with patch.object(
            weatherforecast.csc.WeatherForecastCSC,
            "make_prediction",
            side_effect=fail_prediction,
        ):
            async with self.make_csc(
                initial_state=salobj.State.ENABLED,
                simulation_mode=1,
                config_dir=TEST_CONFIG_DIR,
            ):
                await self.assert_next_summary_state(state=salobj.State.FAULT, timeout=TIMEOUT)

    async def test_prediction_without_meteoblue(self) -> None:
        os.environ.pop("METEOBLUE_API_KEY")
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=1,
            config_dir=TEST_CONFIG_DIR,
            override="disable_meteoblue.yaml",
        ):
            prediction = await self.assert_next_sample(topic=self.remote.tel_nbeats, timeout=TIMEOUT)
            assert len(prediction.timestamp) == 26
            assert prediction.timestamp[1] - prediction.timestamp[0] == approx(1800)
            assert prediction.temperature == approx(list(range(1, 27)))
            assert all(math.isfinite(timestamp) for timestamp in prediction.timestamp)
            for topic in (self.remote.tel_hourlyTrend, self.remote.tel_dailyTrend):
                with self.assertRaises(asyncio.TimeoutError):
                    await topic.next(flush=False, timeout=0.2)

    async def test_prediction_http_failure_faults_csc(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=3,
            config_dir=TEST_CONFIG_DIR,
            override="disable_meteoblue.yaml",
        ):
            await self.assert_next_summary_state(state=salobj.State.ENABLED, timeout=TIMEOUT)
            await self.assert_next_summary_state(state=salobj.State.FAULT, timeout=TIMEOUT)

    def check_arrays(self, response: dict, expected: dict, length: int) -> None:
        missing_names = []
        for name, values in vars(response).items():
            name2 = name.lower()
            name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            if name in expected:
                assert values[:length] == approx(expected[name][:length])
            elif name == "timestamp":
                converted_timestamps = [
                    datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
                    .replace(tzinfo=ZoneInfo("America/Santiago"))
                    .timestamp()
                    for timestamp in expected["time"]
                ]
                assert values[:length] == approx(converted_timestamps[:length])
            elif name.startswith("private"):
                pass
            elif name2 in expected:
                assert values[:length] == approx(expected[name2][:length])
            elif name == "extra_terrestrial_radiation_backwards":
                assert values[:length] == approx(expected["extraterrestrialradiation_backwards"][:length])
            elif name == "total_cloud_cover_spread":
                assert values[:length] == approx(expected["totalcloudcover_spread"][:length])
            elif name == "high_clouds":
                assert values[:length] == approx(expected["hiclouds"][:length])
            elif name == "reference_evapo_transpiration_fao":
                assert values[:length] == approx(expected["referenceevapotranspiration_fao"][:length])
            else:
                missing_names.append(name)

    async def test_telemetry(self) -> None:
        test_file = pathlib.Path("python/lsst/ts/weatherforecast/data/forecast-test.json")
        async with self.make_csc(
            initial_state=salobj.State.ENABLED,
            simulation_mode=1,
            config_dir=TEST_CONFIG_DIR,
        ):
            metadata = await self.assert_next_sample(topic=self.remote.tel_metadata, timeout=TIMEOUT)
            assert approx(-30.24) == metadata.latitude
            assert approx(-70.34) == metadata.longitude
            assert 2298 == metadata.height
            assert "GMT-03" == metadata.timezoneAbbrevation
            assert -3 == metadata.timeOffset

            hourly_trend = await self.assert_next_sample(topic=self.remote.tel_hourlyTrend, timeout=TIMEOUT)
            daily_trend = await self.assert_next_sample(topic=self.remote.tel_dailyTrend, timeout=TIMEOUT)
            with open(test_file) as f:
                df = json.load(f)

            hourly_trend_fld = df["trend_1h"]
            self.check_arrays(
                hourly_trend,
                hourly_trend_fld,
                weatherforecast.GUARANTEED_HOURLY_TREND_LENGTH,
            )

            prediction = await self.assert_next_sample(topic=self.remote.tel_nbeats, timeout=TIMEOUT)
            start = self.csc.convert_time(hourly_trend_fld["time"][0])
            assert prediction.timestamp == approx([start + 1800 * index for index in range(1, 27)])
            assert prediction.temperature == approx(list(range(1, 27)))

            daily_trend_fld = df["trend_day"]
            self.check_arrays(
                daily_trend,
                daily_trend_fld,
                weatherforecast.GUARANTEED_DAILY_TREND_LENGTH,
            )
