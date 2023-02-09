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

__all__ = ["MockServer"]

import json
import logging
import pathlib

from aiohttp import web

REQUEST_URL = "/packages/trendpro-1h_trendpro-day"


class MockServer:
    """Implement the mock Meteoblue API.

    Parameters
    ----------
    port : `int`
        The port that the server starts on.

    Attributes
    ----------
    port : `int`
        The port that the server starts on.
    runner : `None`
        The webapp runner.
    site : `None`
        The webapp site object.
    """

    def __init__(self, port=0) -> None:
        self.port = port
        self.runner = None
        self.site = None
        test_file = pathlib.Path(
            "python/lsst/ts/weatherforecast/data/forecast-test.json"
        )
        self.retries = 0
        self.log = logging.getLogger(__name__)
        with open(test_file) as f:
            self.response = json.load(f)

    def make_app(self):
        """Make the app.

        Returns
        -------
        app : `web.Application`
            The app with the routes added.
        """
        app = web.Application()
        app.add_routes([web.get(REQUEST_URL, self.get_forecast)])
        return app

    async def start(self):
        """Start the server."""
        if self.runner is not None:
            raise RuntimeError("Application already started.")
        app = self.make_app()
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", port=self.port)
        await self.site.start()
        if self.port == 0:
            server = self.site._server
            if len(server.sockets) != 1:
                raise RuntimeError(
                    "Serving on more than one socket; cannot determine the port."
                )
            self.port = server.sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"

    async def cleanup(self):
        """Clean up the server."""
        if self.runner is not None:
            runner = self.runner
            self.runner = None
            await runner.cleanup()

    def get_forecast(self, request):
        """Return the canned json response.

        Parameters
        ----------
        request : `web.Request`
            The request with the URL parameters.

        Returns
        -------
        `web.Response`
            The canned json response.
            See the test file in the data directory for the format.
        """
        while self.retries <= 3:
            self.log.info(f"Inside bad request check. {self.retries=}")
            self.retries += 1
            raise web.HTTPBadRequest(reason="Something went wrong.")
        return web.json_response(self.response)
