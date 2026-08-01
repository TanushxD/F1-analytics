-- ============================================
-- DIMENSION TABLES
-- ============================================

DROP TABLE IF EXISTS dim_driver CASCADE;
CREATE TABLE dim_driver (
    driver_key SERIAL PRIMARY KEY,
    driver_id INTEGER NOT NULL UNIQUE,
    driver_ref VARCHAR(100),
    code VARCHAR(10),
    forename VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    dob DATE,
    nationality VARCHAR(100)
);

DROP TABLE IF EXISTS dim_constructor CASCADE;
CREATE TABLE dim_constructor (
    constructor_key SERIAL PRIMARY KEY,
    constructor_id INTEGER NOT NULL UNIQUE,
    constructor_ref VARCHAR(100),
    name VARCHAR(150) NOT NULL,
    nationality VARCHAR(100)
);

DROP TABLE IF EXISTS dim_circuit CASCADE;
CREATE TABLE dim_circuit (
    circuit_key SERIAL PRIMARY KEY,
    circuit_id INTEGER NOT NULL UNIQUE,
    circuit_ref VARCHAR(100),
    name VARCHAR(150) NOT NULL,
    location VARCHAR(150),
    country VARCHAR(100),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    alt INTEGER
);

DROP TABLE IF EXISTS dim_status CASCADE;
CREATE TABLE dim_status (
    status_key SERIAL PRIMARY KEY,
    status_id INTEGER NOT NULL UNIQUE,
    status VARCHAR(100) NOT NULL
);

DROP TABLE IF EXISTS dim_race CASCADE;
CREATE TABLE dim_race (
    race_key SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL UNIQUE,
    circuit_key INTEGER REFERENCES dim_circuit(circuit_key),
    year INTEGER NOT NULL,
    round INTEGER NOT NULL,
    name VARCHAR(150),
    race_date DATE
);