-- ===========================================
-- TABLE BOBOT
-- ===========================================
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

-- ===========================================
-- QUERY UTAMA
-- ===========================================
WITH benchmark AS (
    SELECT employee_id 
    FROM performance_yearly 
    WHERE rating = 5
),

-- === GROWTH DRIVE & RESILIENCE ===
growth_resilience AS (
    SELECT 
        c.employee_id,
        AVG(NULLIF(c.score, '')::NUMERIC) AS GrowthResilienceScore
    FROM competencies_yearly c
    JOIN dim_competency_pillars p ON c.pillar_code = p.pillar_code
    WHERE p.pillar_label ILIKE '%GROWTH DRIVE & RESILIENCE%'
      AND c.score IS NOT NULL
      AND c.score::TEXT ~ '^[0-9]+(\.[0-9]+)?$'
    GROUP BY c.employee_id
),

-- === COGNITIVE POTENTIAL (IQ & TIKI) ===
cognitive AS (
    SELECT 
        employee_id,
        AVG(score_component) AS CognitivePotentialScore
    FROM (
        SELECT 
            employee_id,
            ((CAST(iq AS NUMERIC) - 70) / (140 - 70)) * 100 AS score_component
        FROM profiles_psych
        WHERE iq IS NOT NULL 
          AND iq::TEXT ~ '^[0-9]+(\.[0-9]+)?$'
        
        UNION ALL
        
        SELECT 
            employee_id,
            (CAST(tiki AS NUMERIC) * 10) AS score_component
        FROM profiles_psych
        WHERE tiki IS NOT NULL 
          AND tiki::TEXT ~ '^[0-9]+(\.[0-9]+)?$'
    ) AS combined
    GROUP BY employee_id
),

-- === EXECUTION DRIVE ===
execution AS (
    SELECT 
        employee_id,
        COUNT(*) FILTER (WHERE theme IN ('Achiever','Futuristic','Context')) * 10 AS ExecutionDriveScore
    FROM strengths
    GROUP BY employee_id
),

-- === EXPERIENCE FIT ===
experience AS (
    SELECT 
        employee_id,
        CASE 
            WHEN years_of_service_months >= 36 THEN 1.0
            WHEN years_of_service_months >= 12 THEN 0.7
            ELSE 0.4
        END AS ExperienceFitScore
    FROM employees
    WHERE years_of_service_months IS NOT NULL
),

-- === GABUNG SEMUA ===
tgv AS (
    SELECT 
        e.employee_id,
        COALESCE(g.GrowthResilienceScore, 0) AS GrowthResilienceScore,
        COALESCE(c.CognitivePotentialScore, 0) AS CognitivePotentialScore,
        COALESCE(ex.ExecutionDriveScore, 0) AS ExecutionDriveScore,
        COALESCE(xp.ExperienceFitScore, 0) AS ExperienceFitScore
    FROM employees e
    LEFT JOIN growth_resilience g ON e.employee_id = g.employee_id
    LEFT JOIN cognitive c ON e.employee_id = c.employee_id
    LEFT JOIN execution ex ON e.employee_id = ex.employee_id
    LEFT JOIN experience xp ON e.employee_id = xp.employee_id
)

-- ===========================================
-- OUTPUT FINAL
-- ===========================================
SELECT 
    t.employee_id,
    ROUND(
          t.GrowthResilienceScore  * (SELECT weight FROM weight_config WHERE tgv_name='GrowthResilience')
        + t.CognitivePotentialScore * (SELECT weight FROM weight_config WHERE tgv_name='CognitivePotential')
        + t.ExecutionDriveScore     * (SELECT weight FROM weight_config WHERE tgv_name='ExecutionDrive')
        + t.ExperienceFitScore      * (SELECT weight FROM weight_config WHERE tgv_name='ExperienceFit'),
    2) AS SuccessScore,
    t.GrowthResilienceScore,
    t.CognitivePotentialScore,
    t.ExecutionDriveScore,
    t.ExperienceFitScore
FROM tgv t
ORDER BY SuccessScore DESC;
