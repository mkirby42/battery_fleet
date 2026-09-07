from dataclasses import dataclass


@dataclass
class UnitHealth:
    """
    Slowly changing battery capability.

    These values may degrade over time due to age, cycling,
    temperature, or other effects.
    """
    available_capacity_kilowatt_hours: float
    max_charge_power_watts: float
    max_discharge_power_watts: float
    charge_efficiency_fraction: float
    discharge_efficiency_fraction: float
    cumulative_energy_throughput_kwh: float = 0.0
    equivalent_full_cycles: float = 0.0


@dataclass
class UnitPolicy:
    """
    Operational/user constraints.

    These are not physical battery properties and may change
    dynamically over time.
    """
    reserve_state_of_charge_fraction: float = 0.20
    grid_charging_allowed: bool = True
    grid_discharging_allowed: bool = True


@dataclass
class UnitState:
    """
    Fast-changing operational state.
    """
    time_unix: float
    state_of_charge_fraction: float

    # Sign convention:
    #   > 0 W = charging battery
    #   < 0 W = discharging battery
    #   = 0 W = idle
    commanded_power_watts: float = 0.0
    actual_power_watts: float = 0.0

    network_reachable: bool = True


class BatteryUnit:
    def __init__(
        self,
        unit_id: str,
        manufacture_lot_id: str,
        nominal_capacity_kilowatt_hours: float,
        nominal_max_charge_power_watts: float,
        nominal_max_discharge_power_watts: float,
        initial_time_unix: float,
        charge_efficiency_fraction: float = 0.95,
        discharge_efficiency_fraction: float = 0.95,
        initial_state_of_charge_fraction: float = 0.50,
        reserve_state_of_charge_fraction: float = 0.20,
    ):
        # Identity
        self.unit_id = unit_id
        self.manufacture_lot_id = manufacture_lot_id

        # Nominal manufactured specifications
        self.nominal_capacity_kilowatt_hours = (
            nominal_capacity_kilowatt_hours
        )
        self.nominal_max_charge_power_watts = (
            nominal_max_charge_power_watts
        )
        self.nominal_max_discharge_power_watts = (
            nominal_max_discharge_power_watts
        )

        # Slowly varying physical capability
        self.health = UnitHealth(
            available_capacity_kilowatt_hours=(
                nominal_capacity_kilowatt_hours
            ),
            max_charge_power_watts=nominal_max_charge_power_watts,
            max_discharge_power_watts=nominal_max_discharge_power_watts,
            charge_efficiency_fraction=charge_efficiency_fraction,
            discharge_efficiency_fraction=discharge_efficiency_fraction,
        )

        # User/operator policy
        self.policy = UnitPolicy(
            reserve_state_of_charge_fraction=(
                reserve_state_of_charge_fraction
            )
        )

        # Fast-changing operating state
        self.state = UnitState(
            time_unix=initial_time_unix,
            state_of_charge_fraction=(
                initial_state_of_charge_fraction
            ),
        )

        self._validate_parameters()

    def _validate_parameters(self):
        if self.nominal_capacity_kilowatt_hours <= 0:
            raise ValueError("Battery capacity must be positive.")

        if self.health.max_charge_power_watts < 0:
            raise ValueError("Max charge power must be non-negative.")

        if self.health.max_discharge_power_watts < 0:
            raise ValueError("Max discharge power must be non-negative.")

        if not 0 < self.health.charge_efficiency_fraction <= 1:
            raise ValueError(
                "Charge efficiency must be between 0 and 1."
            )

        if not 0 < self.health.discharge_efficiency_fraction <= 1:
            raise ValueError(
                "Discharge efficiency must be between 0 and 1."
            )

        if not 0 <= self.state.state_of_charge_fraction <= 1:
            raise ValueError(
                "Initial SOC must be between 0 and 1."
            )

        if not 0 <= self.policy.reserve_state_of_charge_fraction <= 1:
            raise ValueError(
                "Reserve SOC must be between 0 and 1."
            )

    def go_offline(self):
        self.state.network_reachable = False

    def come_online(self):
        self.state.network_reachable = True

    def command_power_watts(self, power_watts: float):
        """
        Deliver a new setpoint over the network.

        If the unit is unreachable, the packet does not land.
        Last commanded power is unchanged. The inverter keeps
        following that last command on the next step().
        """
        if not self.state.network_reachable:
            return

        self.state.commanded_power_watts = power_watts

    def step(self, delta_t_seconds: float):
        """
        Advance this battery by one simulation timestep.
        """
        if delta_t_seconds <= 0:
            raise ValueError(
                "delta_t_seconds must be positive."
            )

        delta_t_hours = delta_t_seconds / 3600.0

        actual_power_watts = self._resolve_actual_power_watts(
            delta_t_hours
        )

        self.state.actual_power_watts = actual_power_watts

        self._update_state_of_charge(
            actual_power_watts,
            delta_t_hours,
        )

        self._update_energy_throughput(
            actual_power_watts,
            delta_t_hours,
        )

        self.state.time_unix += delta_t_seconds

    def _resolve_actual_power_watts(
        self,
        delta_t_hours: float,
    ) -> float:
        """
        Convert commanded power into physically and operationally
        feasible actual power.

        Network reachability is not checked here. Offline only
        blocks new commands; the last setpoint still runs.
        """
        commanded = self.state.commanded_power_watts

        if commanded > 0:
            return min(
                commanded,
                self.charge_headroom_watts(delta_t_hours),
            )

        if commanded < 0:
            return -min(
                -commanded,
                self.discharge_headroom_watts(delta_t_hours),
            )

        return 0.0

    def charge_headroom_watts(self, delta_t_hours: float) -> float:
        if not self.policy.grid_charging_allowed:
            return 0.0

        available_storage_kwh = (
            1.0
            - self.state.state_of_charge_fraction
        ) * self.health.available_capacity_kilowatt_hours

        max_grid_energy_kwh = (
            available_storage_kwh
            / self.health.charge_efficiency_fraction
        )

        max_power_from_soc_watts = (
            max_grid_energy_kwh
            / delta_t_hours
            * 1000.0
        )

        return min(
            self.health.max_charge_power_watts,
            max_power_from_soc_watts,
        )

    def discharge_headroom_watts(self, delta_t_hours: float) -> float:
        """Largest discharge this unit can do this step, as a positive watts."""
        if not self.policy.grid_discharging_allowed:
            return 0.0

        dispatchable_soc = max(
            0.0,
            self.state.state_of_charge_fraction
            - self.policy.reserve_state_of_charge_fraction,
        )

        dispatchable_stored_energy_kwh = (
            dispatchable_soc
            * self.health.available_capacity_kilowatt_hours
        )

        max_deliverable_energy_kwh = (
            dispatchable_stored_energy_kwh
            * self.health.discharge_efficiency_fraction
        )

        max_power_from_soc_watts = (
            max_deliverable_energy_kwh
            / delta_t_hours
            * 1000.0
        )

        return min(
            self.health.max_discharge_power_watts,
            max_power_from_soc_watts,
        )

    def _update_state_of_charge(
        self,
        actual_power_watts: float,
        delta_t_hours: float,
    ):
        power_kw = actual_power_watts / 1000.0

        charge_power_kw = max(
            power_kw,
            0.0,
        )

        discharge_power_kw = max(
            -power_kw,
            0.0,
        )

        capacity_kwh = (
            self.health.available_capacity_kilowatt_hours
        )

        stored_energy_change_kwh = (
            self.health.charge_efficiency_fraction
            * charge_power_kw
            -
            discharge_power_kw
            / self.health.discharge_efficiency_fraction
        ) * delta_t_hours

        delta_soc = (
            stored_energy_change_kwh
            / capacity_kwh
        )

        new_soc = (
            self.state.state_of_charge_fraction
            + delta_soc
        )

        self.state.state_of_charge_fraction = max(
            0.0,
            min(
                1.0,
                new_soc,
            ),
        )

    def _update_energy_throughput(
        self,
        actual_power_watts: float,
        delta_t_hours: float,
    ):
        """
        Track external energy throughput.

        This gives us a simple metric that can later drive
        degradation models.
        """
        energy_kwh = (
            abs(actual_power_watts)
            / 1000.0
            * delta_t_hours
        )

        self.health.cumulative_energy_throughput_kwh += energy_kwh

        full_cycle_throughput_kwh = (
            2.0
            * self.nominal_capacity_kilowatt_hours
        )

        self.health.equivalent_full_cycles = (
            self.health.cumulative_energy_throughput_kwh
            / full_cycle_throughput_kwh
        )
