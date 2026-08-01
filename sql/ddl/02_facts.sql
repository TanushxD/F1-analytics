-- ============================================
-- FACT TABLES
-- ============================================

DROP TABLE IF EXISTS fact_race_results CASCADE;
CREATE TABLE fact_race_results (
    result_key SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL UNIQUE,
    race_key INTEGER NOT NULL REFERENCES dim_race(race_key),
    driver_key INTEGER NOT NULL REFERENCES dim_driver(driver_key),
    constructor_key INTEGER NOT NULL REFERENCES dim_constructor(constructor_key),
    status_key INTEGER REFERENCES dim_status(status_key),
    grid INTEGER,
    position INTEGER,
    position_order INTEGER,
    points NUMERIC(6,2),
    laps INTEGER,
    time_text VARCHAR(50),
    milliseconds INTEGER,
    fastest_lap INTEGER,
    rank INTEGER,
    fastest_lap_time_text VARCHAR(20),
    fastest_lap_ms INTEGER,
    fastest_lap_speed NUMERIC(8,3)
);

DROP TABLE IF EXISTS fact_qualifying CASCADE;
CREATE TABLE fact_qualifying (
    qualify_key SERIAL PRIMARY KEY,
    qualify_id INTEGER NOT NULL UNIQUE,
    race_key INTEGER NOT NULL REFERENCES dim_race(race_key),
    driver_key INTEGER NOT NULL REFERENCES dim_driver(driver_key),
    constructor_key INTEGER NOT NULL REFERENCES dim_constructor(constructor_key),
    position INTEGER,
    q1_text VARCHAR(20),
    q2_text VARCHAR(20),
    q3_text VARCHAR(20),
    q1_ms INTEGER,
    q2_ms INTEGER,
    q3_ms INTEGER
);