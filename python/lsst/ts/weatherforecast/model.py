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

__all__ = ["BobDobbs"]

import os
import random
from asyncio import to_thread
from typing import Any

import pandas as pd
from lsst_efd_client import EfdClient
from prophet import Prophet

from .utils import efd_sites


class MockClient:
    """Implements a mock client for the EFD."""

    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:
        pass

    async def query(self, *args: Any, **kwargs: dict[str, Any]) -> pd.DataFrame:
        """Return a fake response to mock query."""
        data = pd.DataFrame()
        data["mean_temperature"] = [random.uniform(-5, 5) for _ in range(1008)]
        return data


class BobDobbs:
    """Implements prophet model integration."""

    def __init__(self, simulation_mode: int = 0):
        self.model: None | Prophet = None
        self.client: None | EfdClient = None
        self.simulation_mode: int = simulation_mode

    def create_client(self) -> None:
        """Create the EFD client."""
        efd_uri = efd_sites[os.getenv("SITE", "test")]
        if efd_uri in ["summit_efd", "summit_efd_copy"]:
            self.client = EfdClient(efd_uri)
        else:
            self.client = EfdClient("summit_efd_copy", client=MockClient())

    async def query(self) -> pd.DataFrame:
        """Return the results from the EFD."""
        assert self.client is not None
        query = " ".join(
            (
                "SELECT mean(temperatureItem0) as mean_temperature FROM",
                "lsst.sal.ESS.temperature",
                "where salIndex=301 AND time > now() - 7d GROUP BY time(1m) FILL(linear)",
            )
        )
        results = await self.client.influx_client.query(query)
        return results

    def configure_model(self) -> None:
        """Configure the prophet model."""
        self.model = Prophet(
            yearly_seasonality=False,
            daily_seasonality=True,
            weekly_seasonality=False,
            changepoint_range=0.95,
            changepoint_prior_scale=0.05,
        )
        self.model.add_seasonality(
            name="monthly",
            period=3,
            fourier_order=8,
            prior_scale=0.05,  # <-- tweak this
        )

    def predict(self) -> pd.DataFrame:
        """Generate the prediction."""
        assert self.model is not None
        data = self.model.make_future_dataframe(periods=288, freq="5min", include_history=False)
        return self.model.predict(data)

    def fit(self, data: pd.DataFrame) -> None:
        """Fit the model with data."""
        assert self.model is not None
        self.model.fit(data)

    def setup_fit(self, results: pd.DataFrame) -> pd.DataFrame:
        """Setup the data to be fitted."""
        results.insert(0, "ds", results.index)
        results.index = range(0, results.shape[0])
        series = pd.to_datetime(results["ds"])
        naive_series = series.dt.tz_localize(None)
        results["ds"] = naive_series
        results = results.rename(columns={"mean_temperature": "y"})
        # results["unique_id"] = "Temperature"
        return results

    async def do_prediction(self) -> pd.DataFrame:
        """Return the prediction after setting everything up."""
        results = await self.query()
        self.configure_model()
        assert self.model is not None
        results = self.setup_fit(results)
        await to_thread(self.model.fit, results)
        prediction = await to_thread(self.model.predict)
        return prediction
