import datetime

from lsst.ts import salobj

class WeatherForecastCSC(salobj.ConfigurableCSC):
    valid_simulation_mode = (0,)
    def __init__(self, initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=0) -> None:
        super().__init__(name="WeatherForecast", index=None, initial_state=initial_state, config_dir=config_dir, simulation_mode=simulation_mode)
        self.last_time = datetime.date()
        self.interval = 0
        

    def telemetry(self):
        pass
