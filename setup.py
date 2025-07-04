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

from importlib import metadata

import setuptools
import setuptools_scm

scm_version = metadata.version("setuptools_scm")

if scm_version.startswith("8"):
    setuptools.setup(
        version=setuptools_scm.get_version(
            version_file="python/lsst/ts/weatherforecast/version.py",
            relative_to="pyproject.toml",
        )
    )
else:
    setuptools.setup(version=setuptools_scm.get_version(write_to="python/lsst/ts/weatherforecast/version.py"))
