__all__ = ["WeatherForecastCSC"]

import os
import datetime
import asyncio
import aiohttp
import json
import calendar

from . import __version__

from lsst.ts import salobj, utils

API_KEY = os.getenv("METEOBLUE_API_KEY")
LATITUDE = -30.24
LONGITUDE = -70.336
ELEVATION = 2925
TIMEZONE = "America/Santiago"
SITE_URL = "https://my.meteoblue.com/packages/trend-1h"
FORMAT = "json"


class WeatherForecastCSC(salobj.BaseCsc):
    valid_simulation_modes = [0, 1]
    version = __version__

    def __init__(self, initial_state=salobj.State.STANDBY, simulation_mode=0) -> None:
        super().__init__(
            name="WeatherForecast",
            index=None,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )
        self.telemetry_task = utils.make_done_future()
        self.last_time = None
        self.interval = 0

    async def telemetry(self):
        if self.simulation_mode == 1:
            with open("forecast-test.json") as f:
                df = json.load(f)
        else:
            params = {"lat": LATITUDE, "lon": LONGITUDE, "apikey": API_KEY}
            async with aiohttp.ClientSession(
                "http://my.meteoblue.com", raise_for_status=True
            ) as session:
                async with session.get(
                    "/packages/trendpro-1h_trendpro-day", params=params
                ) as resp:
                    with open("forecast.json", "wb") as fd:
                        async for chunk in resp.content.iter_chunked(1024):
                            fd.write(chunk)
            with open("forecast.json") as f:
                df = json.load(f)
        metadata_fld = df["metadata"]
        modelrun_utc = datetime.datetime.strptime(
            metadata_fld["modelrun_utc"], "%Y-%m-%d %H:%M"
        )
        modelrun_utc = calendar.timegm(modelrun_utc.utctimetuple())
        modelrun_updatetime_utc = datetime.datetime.strptime(
            metadata_fld["modelrun_updatetime_utc"], "%Y-%m-%d %H:%M"
        )
        modelrun_updatetime_utc = calendar.timegm(
            modelrun_updatetime_utc.utctimetuple()
        )
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
            timestamp = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M")
            timestamp = calendar.timegm(timestamp.utctimetuple())
            converted_timestamp.append(timestamp)
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
            extraTerrestrialRadiationBackwards=trend_hour_fld[
                "extraterrestrialradiation_backwards"
            ],
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
            referenceEvapoTransipirationFao=trend_hour_fld[
                "referenceevapotranspiration_fao"
            ],
        )
        trend_daily_fld = df["trend_day"]
        timestamp = trend_daily_fld["time"]
        converted_timestamp = []
        for stamp in timestamp:
            timestamp = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M")
            timestamp = calendar.timegm(timestamp.utctimetuple())
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
            visbilityMean=trend_daily_fld["visibility_mean"],
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
        await asyncio.sleep(12 * 3600)

    async def handle_summary_state(self):
        if self.disabled_or_enabled:
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            self.telemetry_task.cancel()
