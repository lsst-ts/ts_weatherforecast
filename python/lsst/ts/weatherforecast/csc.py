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

__all__ = ["WeatherForecastCSC", "execute_csc"]

import asyncio
import datetime
import io
import json
import os
import pathlib

import aiohttp
from aiohttp import web
from lsst.ts import salobj, utils

from . import __version__

API_KEY = os.getenv("METEOBLUE_API_KEY", "")
LATITUDE = -30.24
LONGITUDE = -70.336
ELEVATION = 2925
TIMEZONE = "America/Santiago"
SITE_URL = "https://my.meteoblue.com"
FORMAT = "json"


def execute_csc():
    """Execute the CSC."""
    asyncio.run(WeatherForecastCSC.amain(index=False))


async def get_forecast(request):
    """Return a json str that gives forecast information.

    Parameters
    ----------
    request : `web.Request`
        The request containing url parameters and data.

    Returns
    -------
    web.Response
        The json str response.
    """
    test_file = pathlib.Path("python/lsst/ts/weatherforecast/data/forecast-test.json")
    with open(test_file) as f:
        df = json.load(f)
    return web.json_response(df)


async def make_app():
    """Make the application with routes.

    Returns
    -------
    app : `web.Application`
        The app containing routes.
    """
    app = web.Application()
    app.add_routes([web.get("/packages/trendpro-1h_trendpro-day", get_forecast)])
    return app


async def start_server():
    """Start the server.

    Returns
    -------
    runner : `web.AppRunner`
        Tracks the state of the application.
    """
    app = await make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8080)
    await site.start()
    return runner


async def stop_server(runner):
    """Stop the server.

    Parameters
    ----------
    runner : `web.AppRunner`
        The runner to cleanup.
    """
    await runner.cleanup()


class WeatherForecastCSC(salobj.BaseCsc):
    """Implement the WeatherForecast CSC.

    The WeatherForecast Commandable SAL Component simply streams forecast
    information from the Meteoblue API service.
    It uses an API Key to authenticate with the web service.
    It then publishes the data to the EFD via SAL telemetry.

    Parameters
    ----------
    initial_state : `salobj.State`
        The initial state that the CSC starts in.
    simulation_mode : `int`
        Whether the CSC is in simulation mode.

    Attributes
    ----------
    telemetry_task : `asyncio.Future`
        A task that handles the telemetry loop.
    last_time : `None`
        The last time that the forecast was updated. (UTC)
    interval : `int`
        The interval at which the telemetry loop is run. (Seconds)
    mock_server_running : `bool`
        Is the mock server running?
    """

    valid_simulation_modes = [0, 1]
    version = __version__
    enable_cmdline_state = True

    def __init__(self, initial_state=salobj.State.STANDBY, simulation_mode=0) -> None:
        super().__init__(
            name="WeatherForecast",
            index=None,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )
        self.telemetry_task = utils.make_done_future()
        self.last_time = None
        self.interval = 12 * 3600
        self.mock_server_running = False

    def convert_time(self, timestamp):
        """Convert string to datetime object and then convert to unix
        timestamp.

        Parameters
        ----------
        timestamp : `str`
            The time to convert.
        """
        timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        timestamp = timestamp.timestamp()
        return timestamp

    async def telemetry(self):
        """Implement telemetry loop.

        Download the forecast information from the Meteoblue API to memory.
        Clean up the data for DDS publication.
        Take data from json format and publish to DDS telemetry items.
        """
        try:
            if self.simulation_mode:
                global SITE_URL
                SITE_URL = "http://127.0.0.1:8080"
            self.log.info(f"{SITE_URL=}, {LATITUDE=}, {LONGITUDE=}, {API_KEY=}")
            params = {"lat": LATITUDE, "lon": LONGITUDE, "apikey": API_KEY}
            async with aiohttp.ClientSession(
                SITE_URL, raise_for_status=True
            ) as session:
                async with session.get(
                    "/packages/trendpro-1h_trendpro-day",
                    params=params,
                ) as resp:
                    self.log.info("Session gotten.")
                    fd = io.StringIO()
                    async for chunk in resp.content.iter_chunked(1024):
                        decoded_chunk = chunk.decode()
                        fd.write(decoded_chunk)
            fd.seek(0)
            df = fd.read()
            df = json.loads(df)
            metadata_fld = df["metadata"]
            modelrun_utc = datetime.datetime.strptime(
                metadata_fld["modelrun_utc"], "%Y-%m-%d %H:%M"
            )
            modelrun_utc = modelrun_utc.timestamp()
            modelrun_updatetime_utc = datetime.datetime.strptime(
                metadata_fld["modelrun_updatetime_utc"], "%Y-%m-%d %H:%M"
            )
            modelrun_updatetime_utc = modelrun_updatetime_utc.timestamp()
            await self.tel_metadata.set_write(
                latitude=metadata_fld["latitude"],
                longitude=metadata_fld["longitude"],
                height=metadata_fld["height"],
                timezoneAbbrevation=metadata_fld["timezone_abbrevation"],
                timeOffset=int(metadata_fld["utc_timeoffset"]),
                modelrun=modelrun_utc,
                modelrunUpdatetime=modelrun_updatetime_utc,
            )
            trend_hour_fld = df["trend_1h"]
            timestamp = trend_hour_fld["time"]
            converted_timestamp = []
            for stamp in timestamp:
                timestamp = self.convert_time(stamp)
                converted_timestamp.append(timestamp)
            # check for None in extraTerrestrialRadiationBackwards
            cleaned_extra_terrestrial_radiation_backwards = []
            for value in trend_hour_fld["extraterrestrialradiation_backwards"]:
                if value is None:
                    value = 0.0
                    cleaned_extra_terrestrial_radiation_backwards.append(value)
                else:
                    cleaned_extra_terrestrial_radiation_backwards.append(value)
            await self.tel_hourlyTrend.set_write(
                timestamp=converted_timestamp,
                temperature=trend_hour_fld["temperature"],
                temperatureSpread=trend_hour_fld["temperature_spread"],
                precipitation=trend_hour_fld["precipitation"],
                precipitationSpread=trend_hour_fld["precipitation_spread"],
                windspeed=trend_hour_fld["windspeed"],
                windspeedSpread=trend_hour_fld["windspeed_spread"],
                windDirection=trend_hour_fld["winddirection"],
                seaLevelPressure=trend_hour_fld["sealevelpressure"],
                relativeHumidity=trend_hour_fld["relativehumidity"],
                ghiBackwards=trend_hour_fld["ghi_backwards"],
                extraTerrestrialRadiationBackwards=cleaned_extra_terrestrial_radiation_backwards,
                totalCloudCover=trend_hour_fld["totalcloudcover"],
                totalCloudCoverSpread=trend_hour_fld["totalcloudcover_spread"],
                snowFraction=trend_hour_fld["snowfraction"],
                pictocode=trend_hour_fld["pictocode"],
                gust=trend_hour_fld["gust"],
                lowClouds=trend_hour_fld["lowclouds"],
                midClouds=trend_hour_fld["midclouds"],
                highClouds=trend_hour_fld["hiclouds"],
                sunshineTime=trend_hour_fld["sunshinetime"],
                visibility=trend_hour_fld["visibility"],
                skinTemperature=trend_hour_fld["skintemperature"],
                dewPointTemperature=trend_hour_fld["dewpointtemperature"],
                precipitationProbability=trend_hour_fld["precipitation_probability"],
                cape=trend_hour_fld["cape"],
                liftedIndex=trend_hour_fld["liftedindex"],
                evapoTranspiration=trend_hour_fld["evapotranspiration"],
                referenceEvapoTranspirationFao=trend_hour_fld[
                    "referenceevapotranspiration_fao"
                ],
            )
            trend_daily_fld = df["trend_day"]
            timestamp = trend_daily_fld["time"]
            converted_timestamp = []
            for stamp in timestamp:
                timestamp = self.convert_time(stamp)
                converted_timestamp.append(timestamp)
            await self.tel_dailyTrend.set_write(
                timestamp=converted_timestamp,
                pictocode=trend_daily_fld["pictocode"],
                temperatureMax=trend_daily_fld["temperature_max"],
                temperatureMin=trend_daily_fld["temperature_min"],
                temperatureMean=trend_daily_fld["temperature_mean"],
                temperatureSpread=trend_daily_fld["temperature_spread"],
                precipitation=trend_daily_fld["precipitation"],
                precipitationProbability=trend_daily_fld["precipitation_probability"],
                precipitationSpread=trend_daily_fld["precipitation_spread"],
                windspeedMax=trend_daily_fld["windspeed_max"],
                windspeedMin=trend_daily_fld["windspeed_min"],
                windspeedMean=trend_daily_fld["windspeed_mean"],
                windspeedSpread=trend_daily_fld["windspeed_spread"],
                windDirection=trend_daily_fld["winddirection"],
                seaLevelPressureMax=trend_daily_fld["sealevelpressure_max"],
                seaLevelPressureMin=trend_daily_fld["sealevelpressure_min"],
                seaLevelPressureMean=trend_daily_fld["sealevelpressure_mean"],
                relativeHumidityMax=trend_daily_fld["relativehumidity_max"],
                relativeHumidityMin=trend_daily_fld["relativehumidity_min"],
                relativeHumidityMean=trend_daily_fld["relativehumidity_mean"],
                predictability=trend_daily_fld["predictability"],
                predictabilityClass=trend_daily_fld["predictability_class"],
                totalCloudCoverMax=trend_daily_fld["totalcloudcover_max"],
                totalCloudCoverMin=trend_daily_fld["totalcloudcover_min"],
                totalCloudCoverMean=trend_daily_fld["totalcloudcover_mean"],
                totalCloudCoverSpread=trend_daily_fld["totalcloudcover_spread"],
                snowFraction=trend_daily_fld["snowfraction"],
                ghiTotal=trend_daily_fld["ghi_total"],
                extraTerrestrialRadiationTotal=trend_daily_fld[
                    "extraterrestrialradiation_total"
                ],
                gustMax=trend_daily_fld["gust_max"],
                gustMin=trend_daily_fld["gust_min"],
                gustMean=trend_daily_fld["gust_mean"],
                lowCloudsMax=trend_daily_fld["lowclouds_max"],
                lowCloudsMin=trend_daily_fld["lowclouds_min"],
                lowCloudsMean=trend_daily_fld["lowclouds_mean"],
                midCloudsMax=trend_daily_fld["midclouds_max"],
                midCloudsMin=trend_daily_fld["midclouds_min"],
                midCloudsMean=trend_daily_fld["midclouds_mean"],
                hiCloudsMax=trend_daily_fld["hiclouds_max"],
                hiCloudsMin=trend_daily_fld["hiclouds_min"],
                hiCloudsMean=trend_daily_fld["hiclouds_mean"],
                sunshineTime=trend_daily_fld["sunshinetime"],
                visibilityMax=trend_daily_fld["visibility_max"],
                visibilityMin=trend_daily_fld["visibility_min"],
                visibilityMean=trend_daily_fld["visibility_mean"],
                skinTemperatureMax=trend_daily_fld["skintemperature_max"],
                skinTemperatureMin=trend_daily_fld["skintemperature_min"],
                skinTemperatureMean=trend_daily_fld["skintemperature_mean"],
                dewPointTemperatureMax=trend_daily_fld["dewpointtemperature_max"],
                dewPointTemperatureMin=trend_daily_fld["dewpointtemperature_min"],
                dewPointTemperatureMean=trend_daily_fld["dewpointtemperature_mean"],
                capeMax=trend_daily_fld["cape_max"],
                capeMin=trend_daily_fld["cape_min"],
                capeMean=trend_daily_fld["cape_mean"],
                liftedIndexMax=trend_daily_fld["liftedindex_max"],
                liftedIndexMin=trend_daily_fld["liftedindex_min"],
                liftedIndexMean=trend_daily_fld["liftedindex_mean"],
                evapoTranspiration=trend_daily_fld["evapotranspiration"],
                referenceEvapoTranspirationFao=trend_daily_fld[
                    "referenceevapotranspiration_fao"
                ],
            )
            self.last_time = utils.current_tai()
            await asyncio.sleep(self.interval)
        except Exception:
            self.log.exception("Something went wrong")

    async def handle_summary_state(self):
        """Handle summary state transitions.

        If the CSC transitions to the disabled (or enabled) state,
        start the telemetry loop.
        If exiting out of disabled (or enabled) state,
        stop the telemetry loop.
        """
        if self.disabled_or_enabled:
            if not self.mock_server_running and self.simulation_mode:
                self.runner = await start_server()
                self.mock_server_running = True
                # raise RuntimeError("Intentional raise")
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            if self.mock_server_running:
                await stop_server(self.runner)
                self.mock_server_running = False
            self.telemetry_task.cancel()
