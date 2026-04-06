\i datamining/sql/pigmldata_schema.sql

DROP TABLE IF EXISTS datamining_pigmldata_stage;

CREATE TEMP TABLE datamining_pigmldata_stage (
    record_code VARCHAR(120),
    batch_code VARCHAR(120),
    sample_date TIMESTAMPTZ,
    pig_age_days INTEGER,
    avg_weight DOUBLE PRECISION,
    total_feed_quantity DOUBLE PRECISION,
    feeding_count INTEGER,
    avg_feeding_interval_hours DOUBLE PRECISION,
    pen_code VARCHAR(120),
    pen_capacity INTEGER,
    pen_status VARCHAR(20),
    growth_stage VARCHAR(20),
    feed_type_mode VARCHAR(20),
    device_code VARCHAR(120),
    window_days INTEGER
);

\copy datamining_pigmldata_stage (record_code, batch_code, sample_date, pig_age_days, avg_weight, total_feed_quantity, feeding_count, avg_feeding_interval_hours, pen_code, pen_capacity, pen_status, growth_stage, feed_type_mode, device_code, window_days) FROM 'datamining/generated/synthetic_pigmldata.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO growth_growthstage (
    growth_code,
    growth_name,
    date
)
SELECT
    'SYN' || growth_stage,
    'Synthetic ' || growth_stage,
    NOW()
FROM (
    SELECT DISTINCT growth_stage
    FROM datamining_pigmldata_stage
) growth_rows
ON CONFLICT (growth_code) DO UPDATE SET
    growth_name = EXCLUDED.growth_name;

INSERT INTO pen_pen (
    pen_code,
    pen_name,
    capacity,
    status,
    notes,
    date
)
SELECT
    pen_code,
    'Synthetic ' || pen_code,
    pen_capacity,
    pen_status,
    'Synthetic datamining seed',
    NOW()
FROM (
    SELECT DISTINCT
        pen_code,
        pen_capacity,
        pen_status
    FROM datamining_pigmldata_stage
) pen_rows
ON CONFLICT (pen_code) DO UPDATE SET
    capacity = EXCLUDED.capacity,
    status = EXCLUDED.status,
    notes = EXCLUDED.notes;

INSERT INTO batch_pigbatches (
    batch_code,
    batch_name,
    no_of_pigs,
    current_age,
    avg_weight,
    notes,
    pen_code_id,
    growth_stage_id,
    date
)
SELECT
    batch_rows.batch_code,
    'Synthetic ' || batch_rows.batch_code,
    LEAST(batch_rows.pen_capacity + CASE WHEN batch_rows.pen_status = 'occupied' THEN 2 ELSE -1 END, 30),
    batch_rows.max_age,
    batch_rows.avg_weight_mean,
    'Synthetic datamining seed',
    pen_pen.id,
    growth_growthstage.id,
    NOW()
FROM (
    SELECT
        batch_code,
        pen_code,
        MAX(pig_age_days) AS max_age,
        ROUND(AVG(avg_weight)::numeric, 2) AS avg_weight_mean,
        MAX(pen_capacity) AS pen_capacity,
        MAX(pen_status) AS pen_status,
        CASE
            WHEN MAX(CASE growth_stage WHEN 'HOGPRE' THEN 1 WHEN 'STARTER' THEN 2 WHEN 'GROWER' THEN 3 ELSE 4 END) = 1 THEN 'HOGPRE'
            WHEN MAX(CASE growth_stage WHEN 'HOGPRE' THEN 1 WHEN 'STARTER' THEN 2 WHEN 'GROWER' THEN 3 ELSE 4 END) = 2 THEN 'STARTER'
            WHEN MAX(CASE growth_stage WHEN 'HOGPRE' THEN 1 WHEN 'STARTER' THEN 2 WHEN 'GROWER' THEN 3 ELSE 4 END) = 3 THEN 'GROWER'
            ELSE 'FINISHER'
        END AS growth_stage
    FROM datamining_pigmldata_stage
    GROUP BY batch_code, pen_code
) batch_rows
JOIN pen_pen
    ON pen_pen.pen_code = batch_rows.pen_code
JOIN growth_growthstage
    ON growth_growthstage.growth_code = 'SYN' || batch_rows.growth_stage
ON CONFLICT (batch_code) DO UPDATE SET
    current_age = EXCLUDED.current_age,
    avg_weight = EXCLUDED.avg_weight,
    pen_code_id = EXCLUDED.pen_code_id,
    growth_stage_id = EXCLUDED.growth_stage_id,
    notes = EXCLUDED.notes;

INSERT INTO record_record (
    record_code,
    pig_age_days,
    avg_weight,
    date,
    batch_code_id,
    growth_stage_id
)
SELECT
    stage.record_code,
    stage.pig_age_days,
    stage.avg_weight,
    stage.sample_date,
    batch_pigbatches.id,
    growth_growthstage.id
FROM datamining_pigmldata_stage stage
JOIN batch_pigbatches
    ON batch_pigbatches.batch_code = stage.batch_code
JOIN growth_growthstage
    ON growth_growthstage.growth_code = 'SYN' || stage.growth_stage
ON CONFLICT (record_code) DO UPDATE SET
    pig_age_days = EXCLUDED.pig_age_days,
    avg_weight = EXCLUDED.avg_weight,
    date = EXCLUDED.date,
    batch_code_id = EXCLUDED.batch_code_id,
    growth_stage_id = EXCLUDED.growth_stage_id;

INSERT INTO datamining_pigmldata (
    record_code,
    batch_code,
    pen_code,
    sample_date,
    pig_age_days,
    avg_weight,
    total_feed_quantity,
    feeding_count,
    avg_feeding_interval_hours,
    pen_capacity,
    pen_status,
    growth_stage,
    feed_type_mode,
    device_code,
    window_days,
    created_at,
    updated_at,
    record_id
)
SELECT
    stage.record_code,
    stage.batch_code,
    stage.pen_code,
    stage.sample_date,
    stage.pig_age_days,
    stage.avg_weight,
    stage.total_feed_quantity,
    stage.feeding_count,
    stage.avg_feeding_interval_hours,
    stage.pen_capacity,
    stage.pen_status,
    stage.growth_stage,
    stage.feed_type_mode,
    stage.device_code,
    stage.window_days,
    NOW(),
    NOW(),
    record_record.id
FROM datamining_pigmldata_stage stage
JOIN record_record
    ON record_record.record_code = stage.record_code
ON CONFLICT (record_code) DO UPDATE SET
    batch_code = EXCLUDED.batch_code,
    pen_code = EXCLUDED.pen_code,
    sample_date = EXCLUDED.sample_date,
    pig_age_days = EXCLUDED.pig_age_days,
    avg_weight = EXCLUDED.avg_weight,
    total_feed_quantity = EXCLUDED.total_feed_quantity,
    feeding_count = EXCLUDED.feeding_count,
    avg_feeding_interval_hours = EXCLUDED.avg_feeding_interval_hours,
    pen_capacity = EXCLUDED.pen_capacity,
    pen_status = EXCLUDED.pen_status,
    growth_stage = EXCLUDED.growth_stage,
    feed_type_mode = EXCLUDED.feed_type_mode,
    device_code = EXCLUDED.device_code,
    window_days = EXCLUDED.window_days,
    updated_at = NOW(),
    record_id = EXCLUDED.record_id;
