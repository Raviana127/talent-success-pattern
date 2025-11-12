CREATE TABLE IF NOT EXISTS weight_config (
    tgv_name TEXT PRIMARY KEY,
    weight NUMERIC(5,2)
);

INSERT INTO weight_config (tgv_name, weight) VALUES
('GrowthResilience', 0.35),
('CognitivePotential', 0.25),
('ExecutionDrive', 0.25),
('ExperienceFit', 0.15)
ON CONFLICT (tgv_name) DO NOTHING;

WITH benchmark AS (
    SELECT employee_id 
    FROM performance_yearly 
    WHERE rating = 5
),

growth_resilience AS (
    SELECT 
        c.employee_id,
        AVG(c.score::numeric) AS GrowthResilienceScore
    FROM competencies_yearly c
    JOIN dim_competency_pillars p ON c.pillar_code = p.pillar_code
    WHERE p.pillar_label = 'GROWTH DRIVE & RESILIENCE'
    GROUP BY c.employee_id
),

cognitive AS (
    SELECT 
        employee_id,
        AVG(score_component) AS CognitivePotentialScore
    FROM (
        SELECT 
            employee_id, 
            ((iq::numeric - 70) / (140 - 70)) * 100 AS score_component 
        FROM profiles_psych
        WHERE iq IS NOT NULL
        
        UNION ALL
        
        SELECT 
            employee_id,
            (tiki::numeric * 10) AS score_component
        FROM profiles_psych
        WHERE tiki IS NOT NULL
    ) x
    GROUP BY employee_id
),


execution AS (
    SELECT 
        employee_id,
        COUNT(*) FILTER (WHERE theme IN ('Achiever','Futuristic','Context')) * 10 AS ExecutionDriveScore
    FROM strengths
    GROUP BY employee_id
),

experience AS (
    SELECT 
        employee_id,
        CASE 
            WHEN years_of_service_months::numeric >= 36 THEN 1.0
            WHEN years_of_service_months::numeric >= 12 THEN 0.7
            ELSE 0.4
        END AS ExperienceFitScore
    FROM employees
),

tgv AS (
    SELECT 
        e.employee_id,
        COALESCE(g.GrowthResilienceScore,0) AS GrowthResilienceScore,
        COALESCE(c.CognitivePotentialScore,0) AS CognitivePotentialScore,
        COALESCE(ex.ExecutionDriveScore,0) AS ExecutionDriveScore,
        COALESCE(xp.ExperienceFitScore,0) AS ExperienceFitScore
    FROM employees e
    LEFT JOIN growth_resilience g ON e.employee_id = g.employee_id
    LEFT JOIN cognitive c ON e.employee_id = c.employee_id
    LEFT JOIN execution ex ON e.employee_id = ex.employee_id
    LEFT JOIN experience xp ON e.employee_id = xp.employee_id
)

SELECT 
    t.employee_id,
    ROUND(
          t.GrowthResilienceScore  * (SELECT weight FROM weight_config WHERE tgv_name='GrowthResilience')
        + t.CognitivePotentialScore * (SELECT weight FROM weight_config WHERE tgv_name='CognitivePotential')
        + t.ExecutionDriveScore     * (SELECT weight FROM weight_config WHERE tgv_name='ExecutionDrive')
        + t.ExperienceFitScore      * (SELECT weight FROM weight_config WHERE tgv_name='ExperienceFit')
    , 2) AS SuccessScore
FROM tgv t
ORDER BY SuccessScore DESC;