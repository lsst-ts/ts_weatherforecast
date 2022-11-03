import unittest
import os

from lsst.ts import salobj, weatherforecast

from pytest import approx


class WeatherForecastCSCTestCase(
    salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase
):
    def setUp(self):
        os.environ["LSST_SITE"] = "weatherforecast"
        return super().setUp()

    def basic_make_csc(
        self, initial_state, config_dir=None, simulation_mode=1, **kwargs
    ):
        return weatherforecast.csc.WeatherForecastCSC(
            initial_state=initial_state, simulation_mode=simulation_mode
        )

    async def test_telemetry(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            metadata = await self.remote.tel_metadata.aget()
            assert approx(-30.24) == metadata.latitude
            assert approx(-70.34) == metadata.longitude
            assert 2298 == metadata.height
            assert "GMT-03" == metadata.timezoneAbbrevation
            assert -3 == metadata.timeOffset
