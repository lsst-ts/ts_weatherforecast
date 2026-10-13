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

__all__ = [
    "WeatherForecastCSC",
    "execute_csc",
    "GUARANTEED_DAILY_TREND_LENGTH",
    "GUARANTEED_HOURLY_TREND_LENGTH",
    "command_csc",
]

import asyncio
import bisect
import datetime
import math
import os
import pathlib
import types
import zoneinfo
from typing import Any

import aiohttp

from lsst.ts import salobj, utils

from . import __version__
from .config_schema import CONFIG_SCHEMA
from .enums import ErrorCodes, SimulationMode
from .mock_server import MockServer

LATITUDE: float = -30.24
LONGITUDE: float = -70.749
ELEVATION: int = 2650
TIMEZONE: str = "America/Santiago"
SITE_URL: str = "https://my.meteoblue.com"
FORMAT: str = "json"
REQUEST_URL: str = "/packages/trendpro-1h_trendpro-day"
PREDICTION_URL: str = "/weathernbeats/forecast"
COUNT_HOURLY: int = 382
COUNT_DAILY: int = 15
GUARANTEED_HOURLY_TREND_LENGTH: int = 336
GUARANTEED_DAILY_TREND_LENGTH: int = 14


def execute_csc() -> None:
    """Execute the CSC."""
    asyncio.run(WeatherForecastCSC.amain(index=False))


def command_csc() -> None:
    """Command the CSC."""
    asyncio.run(salobj.CscCommander.amain(name="WeatherForecast", index=False))


class WeatherForecastCSC(salobj.ConfigurableCsc):
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

        * 0 - real mode
        * 1 - simulated data
        * 2 - simulated missing data
        * 3 - simulate bad calls to server.

    Attributes
    ----------
    telemetry_task : `asyncio.Future`
        A task that handles the telemetry loop.
    last_time : `None`
        The last time that the forecast was updated. (UTC)
    interval : `int`
        The interval at which the telemetry loop is run. (Seconds)
    mock_server : `None`
        The mock server started if simulation_mode is enabled.
    tel_loop_error_wait_time: `int`
        The wait time for retrying if the API call fails.
    api_key : `str`
        The stored API key for Meteoblue received from an environment variable.
    """

    valid_simulation_modes: tuple = tuple(SimulationMode)
    version: str = __version__
    enable_cmdline_state: bool = True

    def __init__(
        self,
        initial_state: salobj.State = salobj.State.STANDBY,
        simulation_mode: int = 0,
        config_dir: None | pathlib.Path = None,
        override: str = "",
    ) -> None:
        super().__init__(
            name="WeatherForecast",
            index=None,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            override=override,
        )
        self.telemetry_task: asyncio.Future = utils.make_done_future()
        self.prediction_task: asyncio.Future = utils.make_done_future()
        self.last_hour: None | int = None
        self.interval: int = 60
        self.mock_server: None | MockServer = None
        self.tel_loop_error_wait_time: int = 60
        self.max_retries: int = 3
        self.retries: int = 0
        self.already_updated: bool = False
        self.first_time: bool = True
        self.api_key: str | None = os.getenv("METEOBLUE_API_KEY")
        self.weathernbeats_url = os.getenv("WEATHERNBEATS_URL")
        self.hourly_timestamps: list[float] = []
        self.forecast_curve: list[tuple[float, float]] = []
        self.hourly_ready = asyncio.Event()
        self.hourly_lock = asyncio.Lock()
        self.disable_meteoblue = False

    @staticmethod
    def get_config_pkg() -> str:
        """Return the name of the configuration repository.

        Returns
        -------
        `str`
            The name of the configuration repository.
        """
        return "ts_config_ocs"

    async def configure(self, config: types.SimpleNamespace) -> None:
        """Configure the CSC."""
        self.tel_loop_error_wait_time = config.tel_loop_error_wait_time
        self.disable_meteoblue = config.disable_meteoblue
        if not self.disable_meteoblue and self.api_key is None:
            raise RuntimeError("METEOBLUE_API_KEY must be defined.")

    def convert_time(self, timestamp: str) -> float:
        """Convert timestamp string to unix timestamp.

        This is used to convert the string that MeteoBlue returns for time
        into a timestamp that can be published over DDS.

        Parameters
        ----------
        timestamp : `str`
            The time to convert.

        Returns
        -------
        result : `float`
            A timestamp float converted from string.
        """
        result: float = (
            datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
            .replace(tzinfo=zoneinfo.ZoneInfo("America/Santiago"))
            .timestamp()
        )
        return result

    def cleanup_results(
        self, data: dict[str, list[int | float | None | str]]
    ) -> dict[str, list[float | int | None | str]]:
        """Convert None values to math.nan if found."""
        for field in data:
            data[field] = [math.nan if value is None else value for value in data[field]]
        return data

    async def make_prediction(self) -> list[tuple[float, float]]:
        """Fetch and validate the timestamped temperature curve."""
        if self.simulation_mode:
            assert self.mock_server is not None
            site_url = self.mock_server.url
        else:
            if not self.weathernbeats_url:
                raise RuntimeError("WEATHERNBEATS_URL must be defined.")
            site_url = self.weathernbeats_url.rstrip("/")
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{site_url}{PREDICTION_URL}") as resp:
                resp.raise_for_status()
                body = await resp.json()
        return self.parse_curve(body)

    @staticmethod
    def parse_curve(body: dict[str, Any]) -> list[tuple[float, float]]:
        """Validate a service response for interpolation."""
        rows = body["curve"]
        if not isinstance(rows, list) or len(rows) < 2:
            raise ValueError("Forecast curve must contain at least two points.")
        curve: list[tuple[float, float]] = []
        for row in rows:
            time = datetime.datetime.fromisoformat(row["time"])
            if time.tzinfo is None:
                raise ValueError("Forecast times must include a timezone.")
            timestamp = time.timestamp()
            temperature = float(row["temperature"])
            if not math.isfinite(timestamp) or not math.isfinite(temperature):
                raise ValueError("Forecast curve contains a nonfinite value.")
            if curve and timestamp <= curve[-1][0]:
                raise ValueError("Forecast times must be strictly increasing.")
            curve.append((timestamp, temperature))
        return curve

    @staticmethod
    def temperatures_at_times(curve: list[tuple[float, float]], timestamps: list[float]) -> list[float]:
        """Interpolate within the curve and leave other hours unavailable."""
        times = [point[0] for point in curve]
        temperatures = []
        for timestamp in timestamps:
            if not curve or timestamp < times[0] or timestamp > times[-1]:
                temperatures.append(math.nan)
                continue
            right = bisect.bisect_left(times, timestamp)
            if times[right] == timestamp:
                temperatures.append(curve[right][1])
            else:
                left = right - 1
                fraction = (timestamp - times[left]) / (times[right] - times[left])
                temperatures.append(curve[left][1] + fraction * (curve[right][1] - curve[left][1]))
        return temperatures

    @staticmethod
    def current_hourly_timestamps() -> list[float]:
        """Build a UTC hourly grid when Meteoblue is disabled."""
        now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
        start = now.timestamp()
        return [start + 3600 * index for index in range(GUARANTEED_HOURLY_TREND_LENGTH)]

    async def prediction_loop(self) -> None:
        """Generate a prediction every x seconds."""
        while True:
            try:
                curve = await self.make_prediction()
                if not self.disable_meteoblue:
                    await self.hourly_ready.wait()
                async with self.hourly_lock:
                    self.forecast_curve = curve
                    if self.disable_meteoblue:
                        self.hourly_timestamps = self.current_hourly_timestamps()
                        await self.tel_hourlyTrend.set_write(
                            timestamp=self.hourly_timestamps,
                            temperature=self.temperatures_at_times(curve, self.hourly_timestamps),
                        )
                    else:
                        await self.tel_hourlyTrend.set_write(
                            temperature=self.temperatures_at_times(curve, self.hourly_timestamps)
                        )
            except Exception:
                self.log.exception("Failed to make prediction.")
                await self.fault(
                    code=ErrorCodes.PREDICTION_FAILED, report="Failed to get prediction from weathernbeats."
                )
                raise
            await asyncio.sleep(60 * 15)

    async def write_data(self) -> None:
        """Write the data and publish telemetry."""
        response = await self.get_response()
        assert response is not None
        trend_hourly_fld, trend_daily_fld = self.setup_response(response)
        metadata_fld = response["metadata"]
        modelrun_utc = datetime.datetime.strptime(metadata_fld["modelrun_utc"], "%Y-%m-%d %H:%M").timestamp()
        modelrun_updatetime_utc = datetime.datetime.strptime(
            metadata_fld["modelrun_updatetime_utc"], "%Y-%m-%d %H:%M"
        ).timestamp()
        await self.tel_metadata.set_write(
            latitude=metadata_fld["latitude"],
            longitude=metadata_fld["longitude"],
            height=metadata_fld["height"],
            timezoneAbbrevation=metadata_fld["timezone_abbrevation"],
            timeOffset=int(metadata_fld["utc_timeoffset"]),
            modelrun=str(modelrun_utc),
            modelrunUpdatetime=str(modelrun_updatetime_utc),
        )

        async with self.hourly_lock:
            self.hourly_timestamps = trend_hourly_fld["time"]
            await self.tel_hourlyTrend.set_write(
                timestamp=trend_hourly_fld["time"],
                temperature=self.temperatures_at_times(self.forecast_curve, self.hourly_timestamps),
                temperatureSpread=trend_hourly_fld["temperature_spread"],
                precipitation=trend_hourly_fld["precipitation"],
                precipitationSpread=trend_hourly_fld["precipitation_spread"],
                windspeed=trend_hourly_fld["windspeed"],
                windspeedSpread=trend_hourly_fld["windspeed_spread"],
                windDirection=trend_hourly_fld["winddirection"],
                seaLevelPressure=trend_hourly_fld["sealevelpressure"],
                relativeHumidity=trend_hourly_fld["relativehumidity"],
                ghiBackwards=trend_hourly_fld["ghi_backwards"],
                extraTerrestrialRadiationBackwards=trend_hourly_fld["extraterrestrialradiation_backwards"],
                totalCloudCover=trend_hourly_fld["totalcloudcover"],
                totalCloudCoverSpread=trend_hourly_fld["totalcloudcover_spread"],
                snowFraction=trend_hourly_fld["snowfraction"],
                pictocode=trend_hourly_fld["pictocode"],
                gust=trend_hourly_fld["gust"],
                lowClouds=trend_hourly_fld["lowclouds"],
                midClouds=trend_hourly_fld["midclouds"],
                highClouds=trend_hourly_fld["highclouds"],
                sunshineTime=trend_hourly_fld["sunshinetime"],
                visibility=trend_hourly_fld["visibility"],
                skinTemperature=trend_hourly_fld["skintemperature"],
                dewPointTemperature=trend_hourly_fld["dewpointtemperature"],
                precipitationProbability=trend_hourly_fld["precipitation_probability"],
                cape=trend_hourly_fld["cape"],
                liftedIndex=trend_hourly_fld["liftedindex"],
                evapoTranspiration=trend_hourly_fld["evapotranspiration"],
                referenceEvapoTranspirationFao=trend_hourly_fld["referenceevapotranspiration_fao"],
            )
            self.hourly_ready.set()
        await self.tel_dailyTrend.set_write(
            timestamp=trend_daily_fld["time"],
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
            extraTerrestrialRadiationTotal=trend_daily_fld["extraterrestrialradiation_total"],
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
            referenceEvapoTranspirationFao=trend_daily_fld["referenceevapotranspiration_fao"],
        )

    async def telemetry(self) -> None:
        """Run the telemetry loop."""
        self.first_time = True
        if not self.disable_meteoblue:
            await self.write_data()
        self.first_time = False
        while True:
            time = datetime.datetime.now(tz=zoneinfo.ZoneInfo("America/Santiago"))
            if time.hour in [4, 16] and not self.already_updated:
                if not self.disable_meteoblue:
                    await self.write_data()
                self.last_hour = time.hour
                self.already_updated = True
            else:
                if time.hour != self.last_hour:
                    self.already_updated = False
                await asyncio.sleep(self.interval)

    async def get_response(self) -> dict[str, Any] | None:
        """Get the response from MeteoBlue API.

        Returns
        -------
        response : `dict`[`str`, `Any`]
            The response from MeteoBlue.
        """
        if self.simulation_mode:
            assert self.mock_server is not None
            site_url = self.mock_server.url
        else:
            site_url = SITE_URL
        params = {"lat": LATITUDE, "lon": LONGITUDE, "apikey": self.api_key, "asl": ELEVATION}
        for _ in range(self.max_retries):
            self.log.info(f"Try {_} of {self.max_retries}")
            async with aiohttp.ClientSession(site_url) as session:
                async with session.get(REQUEST_URL, params=params) as resp:
                    try:
                        response = await resp.json()
                        return response
                    except Exception:
                        self.log.exception(
                            f"Failed to get reply. Trying again in {self.tel_loop_error_wait_time} seconds."
                        )
                        await asyncio.sleep(self.tel_loop_error_wait_time)
                        continue
        await self.fault(code=ErrorCodes.METEOBLUE_FAILED, report="Number of retries exceeded.")
        return None

    def setup_response(self, response: dict) -> tuple[dict, dict]:
        """Setup the response to be published.

        * Takes the data and converts any None value to math.nan
        * Converts time strings to timestamps.
        * Cuts the length of the data to the correct size.
        """
        trend_hourly_fld = response["trend_1h"]
        trend_hourly_fld = self.cleanup_results(trend_hourly_fld)
        for name, values in trend_hourly_fld.items():
            trend_hourly_fld[name] = values[:GUARANTEED_HOURLY_TREND_LENGTH]
        timestamps = trend_hourly_fld["time"]
        converted_timestamps = [self.convert_time(str(timestamp)) for timestamp in timestamps]
        trend_hourly_fld["time"] = converted_timestamps  # type: ignore
        trend_daily_fld = response["trend_day"]
        for name, values in trend_daily_fld.items():
            trend_daily_fld[name] = values[:GUARANTEED_DAILY_TREND_LENGTH]
        timestamps = trend_daily_fld["time"]
        converted_timestamps = [self.convert_time(timestamp) for timestamp in timestamps]
        trend_daily_fld["time"] = converted_timestamps
        return trend_hourly_fld, trend_daily_fld

    async def handle_summary_state(self) -> None:
        """Handle summary state transitions.

        If the CSC transitions to the disabled (or enabled) state,
        start the telemetry loop.
        If exiting out of disabled (or enabled) state,
        stop the telemetry loop.
        """
        if self.disabled_or_enabled:
            if self.mock_server is None and self.simulation_mode:
                if self.simulation_mode == 1:
                    self.mock_server = MockServer()
                elif self.simulation_mode == 2:
                    self.mock_server = MockServer(
                        data="python/lsst/ts/weatherforecast/data/forecast-missing.json"
                    )
                elif self.simulation_mode == 3:
                    self.mock_server = MockServer(bad_request=True)
                assert self.mock_server is not None
                self.mock_server.current_prediction = self.disable_meteoblue
                await self.mock_server.start()
            if self.prediction_task.done():
                self.prediction_task = asyncio.create_task(self.prediction_loop())
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            self.telemetry_task.cancel()
            self.prediction_task.cancel()
            self.hourly_ready.clear()
            self.hourly_timestamps = []
            self.forecast_curve = []
            if self.mock_server is not None:
                server = self.mock_server
                self.mock_server = None
                await server.cleanup()
