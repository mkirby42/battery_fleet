def apply_setpoint(
    energy_kwh: float,
    setpoint_kw: float,
    capacity_kwh: float,
    max_charge_kw: float,
    max_discharge_kw: float,
    floor_kwh: float,
    efficiency: float,
    dt_s: float,
) -> tuple[float, float]:
    dt_h = dt_s / 3600.0
    power = max(-max_charge_kw, min(max_discharge_kw, setpoint_kw))
    old_energy = energy_kwh

    if power > 0:
        if efficiency == 1.0:
            new_energy = old_energy - power * dt_h
        else:
            new_energy = old_energy - power * dt_h / efficiency
    elif power < 0:
        if efficiency == 1.0:
            new_energy = old_energy - power * dt_h
        else:
            new_energy = old_energy - power * dt_h * efficiency
    else:
        new_energy = old_energy

    clamped_energy = max(floor_kwh, min(capacity_kwh, new_energy))
    if clamped_energy != new_energy:
        new_energy = clamped_energy
        if efficiency == 1.0:
            power = -(new_energy - old_energy) / dt_h
        else:
            delta = new_energy - old_energy
            if delta < 0:
                power = -delta * efficiency / dt_h
            elif delta > 0:
                power = -delta / (dt_h * efficiency)
            else:
                power = 0.0
    else:
        new_energy = clamped_energy

    return new_energy, power
