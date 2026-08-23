TICK_S = 15
INTERVAL_S = 300
SCHEMA_VERSION = 1


def interval_start(t_s: int) -> int:
    return (t_s // INTERVAL_S) * INTERVAL_S


def ticks_in_interval(interval_s: int = INTERVAL_S) -> int:
    return interval_s // TICK_S
