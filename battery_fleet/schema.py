DDL = """
CREATE TABLE regions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE cities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region_id TEXT NOT NULL
);

CREATE TABLE substations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city_id TEXT NOT NULL
);

CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    substation_id TEXT NOT NULL
);

CREATE TABLE units (
    id TEXT PRIMARY KEY,
    capacity_kwh REAL NOT NULL,
    max_charge_kw REAL NOT NULL,
    max_discharge_kw REAL NOT NULL
);

CREATE TABLE installs (
    unit_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    PRIMARY KEY (unit_id, location_id)
);

CREATE TABLE market_event (
    id TEXT PRIMARY KEY,
    settlement_point TEXT NOT NULL,
    kind TEXT NOT NULL,
    scarcity_start_s INTEGER NOT NULL,
    scarcity_end_s INTEGER NOT NULL,
    scarcity_adder REAL NOT NULL,
    congestion_start_s INTEGER NOT NULL,
    congestion_end_s INTEGER NOT NULL,
    congestion_adder REAL NOT NULL
);

CREATE TABLE prices (
    t_s INTEGER PRIMARY KEY,
    energy REAL NOT NULL,
    scarcity REAL NOT NULL,
    congestion REAL NOT NULL,
    losses REAL NOT NULL
);

CREATE TABLE weather (
    t_s INTEGER NOT NULL,
    city_id TEXT NOT NULL,
    temp_c REAL NOT NULL,
    PRIMARY KEY (t_s, city_id)
);

CREATE TABLE load_model (
    id TEXT PRIMARY KEY,
    formula TEXT NOT NULL
);

CREATE TABLE loads (
    location_id TEXT NOT NULL,
    t_s INTEGER NOT NULL,
    kw REAL NOT NULL,
    PRIMARY KEY (location_id, t_s)
);

CREATE TABLE outages (
    start_s INTEGER NOT NULL,
    end_s INTEGER NOT NULL,
    node_kind TEXT NOT NULL,
    node_id TEXT NOT NULL
);

CREATE TABLE link_plan (
    start_s INTEGER NOT NULL,
    end_s INTEGER NOT NULL,
    location_id TEXT NOT NULL
);

CREATE TABLE battery_model (
    id TEXT PRIMARY KEY,
    efficiency REAL NOT NULL
);

CREATE TABLE market_model (
    id TEXT PRIMARY KEY
);

CREATE TABLE local_policy (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    floor_frac REAL NOT NULL
);

CREATE TABLE hq_policy (
    id TEXT PRIMARY KEY,
    charge_below REAL NOT NULL,
    discharge_above REAL NOT NULL
);

CREATE TABLE run (
    id TEXT PRIMARY KEY,
    seed INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    local_policy_id TEXT NOT NULL,
    hq_policy_id TEXT NOT NULL,
    market_event_id TEXT NOT NULL,
    started_s INTEGER,
    finished_s INTEGER
);

CREATE TABLE ticks (
    t_s INTEGER NOT NULL,
    unit_id TEXT NOT NULL,
    energy_kwh REAL NOT NULL,
    power_kw REAL NOT NULL,
    who_decided TEXT NOT NULL,
    hq_asked_kw REAL,
    shortfall_kwh REAL NOT NULL,
    islanded INTEGER NOT NULL,
    link_up INTEGER NOT NULL,
    PRIMARY KEY (t_s, unit_id)
);

CREATE TABLE events (
    t_s INTEGER NOT NULL,
    kind TEXT NOT NULL,
    unit_id TEXT,
    location_id TEXT,
    detail TEXT NOT NULL
);

CREATE TABLE intervals (
    t_s INTEGER PRIMARY KEY,
    energy_mwh REAL NOT NULL,
    pnl_usd REAL NOT NULL,
    energy REAL NOT NULL,
    scarcity REAL NOT NULL,
    congestion REAL NOT NULL,
    losses REAL NOT NULL,
    spp REAL NOT NULL
);

CREATE TABLE checks (
    name TEXT PRIMARY KEY,
    passed INTEGER NOT NULL,
    detail TEXT NOT NULL
);

CREATE TABLE scoreboard (
    revenue_usd REAL NOT NULL,
    shortfall_kwh REAL NOT NULL,
    coverage REAL NOT NULL,
    locations_dark INTEGER NOT NULL,
    time_at_floor_s INTEGER NOT NULL
);
"""
