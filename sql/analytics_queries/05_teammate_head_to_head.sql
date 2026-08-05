WITH teammate_pairs AS (
    SELECT
        f1.race_key,
        r.year,
        f1.constructor_key,
        f1.driver_key AS driver_a_key,
        f1.position_order AS driver_a_position,
        f2.driver_key AS driver_b_key,
        f2.position_order AS driver_b_position
    FROM fact_race_results f1
    JOIN fact_race_results f2
        ON f1.race_key = f2.race_key
       AND f1.constructor_key = f2.constructor_key
       AND f1.driver_key < f2.driver_key
    JOIN dim_race r ON f1.race_key = r.race_key
),
head_to_head AS (
    SELECT
        constructor_key,
        year,
        driver_a_key,
        driver_b_key,
        COUNT(*) FILTER (WHERE driver_a_position < driver_b_position) AS a_wins,
        COUNT(*) FILTER (WHERE driver_b_position < driver_a_position) AS b_wins,
        COUNT(*) AS races_together
    FROM teammate_pairs
    GROUP BY constructor_key, year, driver_a_key, driver_b_key
)
SELECT
    c.name AS constructor_name,
    h.year,
    da.forename || ' ' || da.surname AS driver_a,
    db.forename || ' ' || db.surname AS driver_b,
    h.a_wins,
    h.b_wins,
    h.races_together
FROM head_to_head h
JOIN dim_constructor c ON h.constructor_key = c.constructor_key
JOIN dim_driver da ON h.driver_a_key = da.driver_key
JOIN dim_driver db ON h.driver_b_key = db.driver_key
WHERE h.year = 2023
ORDER BY h.races_together DESC;