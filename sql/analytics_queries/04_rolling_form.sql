WITH driver_race_points AS (
    SELECT
        d.driver_key,
        d.forename,
        d.surname,
        r.year,
        r.round,
        r.race_date,
        f.points
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
    WHERE r.year = 2023
)
SELECT
    forename,
    surname,
    round,
    race_date,
    points,
    ROUND(
        AVG(points) OVER (
            PARTITION BY driver_key
            ORDER BY round
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_5race_form
FROM driver_race_points
WHERE surname = 'Verstappen'
ORDER BY round;