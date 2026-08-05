WITH race_deltas AS (
    SELECT
        d.driver_key,
        d.forename,
        d.surname,
        r.year,
        f.race_key,
        f.grid,
        f.position_order,
        (f.grid - f.position_order) AS positions_gained
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
    WHERE f.grid > 0
),
driver_season_avg AS (
    SELECT
        driver_key,
        forename,
        surname,
        year,
        COUNT(*) AS races_completed,
        ROUND(AVG(positions_gained), 2) AS avg_positions_gained
    FROM race_deltas
    GROUP BY driver_key, forename, surname, year
    HAVING COUNT(*) >= 5
)
SELECT
    forename,
    surname,
    year,
    races_completed,
    avg_positions_gained,
    DENSE_RANK() OVER (
        PARTITION BY year
        ORDER BY avg_positions_gained DESC
    ) AS overtaking_rank
FROM driver_season_avg
WHERE year = 2023
ORDER BY overtaking_rank;