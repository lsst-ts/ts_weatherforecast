"""Sphinx configuration file for TSSW package"""

from documenteer.conf.pipelinespkg import *  # type: ignore # noqa
from lsst.ts import weatherforecast  # type: ignore # noqa

project = "ts_weatherforecast"
html_theme_options["logotext"] = project
html_title = project
html_short_title = project

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)
