WITH driver_season_points AS (
    SELECT
        d.driver_key,
        d.forename,
        d.surname,
        r.year,
        r.round,
        r.race_date,
        f.points,
        SUM(f.points) OVER (
            PARTITION BY d.driver_key, r.year
            ORDER BY r.round
        ) AS cumulative_points
    FROM fact_race_results f
    JOIN dim_driver d ON f.driver_key = d.driver_key
    JOIN dim_race r ON f.race_key = r.race_key
)
SELECT
    forename,
    surname,
    year,
    round,
    race_date,
    points,
    cumulative_points,
    RANK() OVER (
        PARTITION BY year, round
        ORDER BY cumulative_points DESC
    ) AS championship_rank_after_race
FROM driver_season_points
WHERE year = 2023
ORDER BY round, championship_rank_after_race;