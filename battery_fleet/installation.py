from dataclasses import dataclass

from battery_fleet.battery import BatteryUnit


@dataclass
class InstallationState:
    """
    Site-level electrical state.

    Sign convention for grid power:
        > 0 W = importing from grid
        < 0 W = exporting to grid
    """
    time_unix: float
    user_load_power_watts: float = 0.0
    grid_power_watts: float = 0.0


class Installation:
    def __init__(
        self,
        install_id: str,
        latitude_degrees: float,
        longitude_degrees: float,
        initial_time_unix: float,
        batteries: list[BatteryUnit] | None = None,
    ):
        self.install_id = install_id
        self.latitude_degrees = latitude_degrees
        self.longitude_degrees = longitude_degrees

        if not -90.0 <= latitude_degrees <= 90.0:
            raise ValueError(
                "Latitude must be between -90 and 90."
            )

        if not -180.0 <= longitude_degrees <= 180.0:
            raise ValueError(
                "Longitude must be between -180 and 180."
            )

        self.state = InstallationState(
            time_unix=initial_time_unix,
        )

        self.batteries = []
        for battery in batteries or []:
            self.add_battery(battery)

    def add_battery(
        self,
        battery: BatteryUnit,
    ):
        battery.state.time_unix = self.state.time_unix
        self.batteries.append(
            battery
        )

    def set_user_load_power_watts(
        self,
        power_watts: float,
    ):
        if power_watts < 0:
            raise ValueError(
                "User load must be non-negative."
            )

        self.state.user_load_power_watts = power_watts

    def step(
        self,
        delta_t_seconds: float,
    ):
        """
        Advance every battery at this installation,
        then calculate site/grid power flow.
        """
        if delta_t_seconds <= 0:
            raise ValueError(
                "delta_t_seconds must be positive."
            )

        for battery in self.batteries:
            battery.step(
                delta_t_seconds
            )

        self._update_grid_power()

        self.state.time_unix += delta_t_seconds

    def _update_grid_power(self):
        """
        Site energy balance:

        P_grid =
            P_load
            + sum(P_battery)

        Battery convention:
            > 0 = charging
            < 0 = discharging

        Grid convention:
            > 0 = importing
            < 0 = exporting
        """
        total_battery_power_watts = sum(
            battery.state.actual_power_watts
            for battery in self.batteries
        )

        self.state.grid_power_watts = (
            self.state.user_load_power_watts
            + total_battery_power_watts
        )
