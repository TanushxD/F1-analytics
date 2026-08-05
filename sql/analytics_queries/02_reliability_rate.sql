WITH categorized_results AS (
    SELECT
        c.constructor_key,
        c.name AS constructor_name,
        r.year,
        f.result_id,
        s.status,
        CASE
            WHEN s.status = 'Finished' OR s.status LIKE '+%Lap%' THEN 'Finished'
            WHEN s.status IN ('Accident', 'Collision', 'Spun off', 'Collision damage') THEN 'Accident'
            WHEN s.status IN (
                'Disqualified', 'Excluded', 'Did not qualify', 'Did not prequalify',
                'Not classified', 'Withdrew', 'Not restarted', 'Underweight',
                'Safety concerns', '107% Rule', 'Safety', 'Injured', 'Injury',
                'Fatal accident', 'Eye injury', 'Driver unwell', 'Illness', 'Physical'
            ) THEN 'Other'
            ELSE 'Mechanical'
        END AS status_category
    FROM fact_race_results f
    JOIN dim_constructor c ON f.constructor_key = c.constructor_key
    JOIN dim_race r ON f.race_key = r.race_key
    JOIN dim_status s ON f.status_key = s.status_key
),
constructor_season_summary AS (
    SELECT
        constructor_key,
        constructor_name,
        year,
        COUNT(*) AS total_entries,
        COUNT(*) FILTER (WHERE status_category = 'Mechanical') AS mechanical_failures,
        COUNT(*) FILTER (WHERE status_category = 'Accident') AS accidents,
        COUNT(*) FILTER (WHERE status_category = 'Finished') AS finishes
    FROM categorized_results
    GROUP BY constructor_key, constructor_name, year
)
SELECT
    constructor_name,
    year,
    total_entries,
    mechanical_failures,
    ROUND(mechanical_failures::NUMERIC / total_entries * 100, 1) AS mechanical_failure_rate_pct,
    accidents,
    finishes,
    ROUND(finishes::NUMERIC / total_entries * 100, 1) AS finish_rate_pct
FROM constructor_season_summary
WHERE year = 2023
ORDER BY mechanical_failure_rate_pct DESC;