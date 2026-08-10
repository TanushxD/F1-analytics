DROP VIEW IF EXISTS vw_tableau_main;
CREATE VIEW vw_tableau_main AS
SELECT
    f.result_id,
    d.forename || ' ' || d.surname AS driver_name,
    d.nationality AS driver_nationality,
    c.name AS constructor_name,
    c.nationality AS constructor_nationality,
    ci.name AS circuit_name,
    ci.country AS circuit_country,
    r.year,
    r.round,
    r.race_date,
    r.name AS race_name,
    f.grid,
    f.position_order AS finish_position,
    f.points,
    f.laps,
    s.status,
    CASE
        WHEN s.status = 'Finished' OR s.status LIKE '+%Lap%' THEN 'Finished'
        WHEN s.status IN ('Accident', 'Collision', 'Spun off', 'Collision damage') THEN 'Accident'
        ELSE 'Mechanical/Other'
    END AS status_category,
    (f.grid - f.position_order) AS grid_delta
FROM fact_race_results f
JOIN dim_driver d ON f.driver_key = d.driver_key
JOIN dim_constructor c ON f.constructor_key = c.constructor_key
JOIN dim_race r ON f.race_key = r.race_key
JOIN dim_circuit ci ON r.circuit_key = ci.circuit_key
JOIN dim_status s ON f.status_key = s.status_key
WHERE f.grid > 0 OR f.grid IS NULL;