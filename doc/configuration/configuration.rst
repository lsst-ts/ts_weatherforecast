.. _Configuration_details:

#######################
WeatherForecast Configuration
#######################


Set ``WEATHERNBEATS_URL`` to the reachable HTTP service origin.
The CSC calls ``/weathernbeats/forecast`` under that origin in real operation.
The existing ``METEOBLUE_API_KEY`` remains required for Meteoblue forecasts unless ``disable_meteoblue`` is true. 
With Meteoblue disabled, only the ``nbeats`` forecast topic is published.
