
CREATE TABLE exercises (
    exercise_template_id   TEXT PRIMARY KEY,
    title                   TEXT NOT NULL,
    exercise_type           TEXT,
    primary_muscle_group    TEXT,
    equipment                TEXT,
    is_custom                 BOOLEAN NOT NULL,
    is_quad_relevant           BOOLEAN NOT NULL
);

CREATE TABLE whoop_daily(
    whoop_daily_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whoop_date DATE NOT NULL UNIQUE,
    recovery_score REAL,
    resting_hr REAL,
    hrv_ms REAL,
    daily_strain REAL,
    sleep_performance_pct REAL,
    respiratory_rate REAL,
    asleep_duration_min REAL,
    light_sleep_min REAL,
    deep_sleep_min REAL,
    rem_sleep_min REAL,
    awake_min REAL,
    sleep_need_min REAL,
    sleep_debt_min REAL,
    sleep_efficiency_pct REAL,
    sleep_consistency_pct REAL,
    blood_oxygen_pct REAL,
    skin_temp_c REAL,
    energy_burned_cal REAL,
    max_hr REAL,
    avg_hr REAL,
    in_bed_duration_min REAL
);


CREATE TABLE hevy_workouts (
    workout_id            TEXT PRIMARY KEY,
    title                   TEXT NOT NULL,
    routine_id               TEXT,
    start_time_utc             TIMESTAMP NOT NULL,
    end_time_utc                 TIMESTAMP NOT NULL,
    whoop_daily_id                       INTEGER REFERENCES whoop_daily(whoop_daily_id) ON DELETE SET NULL
);



CREATE TABLE workout_sets (
    set_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id               TEXT NOT NULL REFERENCES hevy_workouts(workout_id) ON DELETE CASCADE,
    exercise_template_id       TEXT NOT NULL REFERENCES exercises(exercise_template_id),
    set_index                    INTEGER NOT NULL,
    set_type                       TEXT,
    weight_kg                        REAL,
    reps                                INTEGER,
    rpe                                   REAL
);

CREATE TABLE whoop_activities (
    activity_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_name             TEXT NOT NULL,
    start_time_local            TIMESTAMP NOT NULL,
    end_time_local                 TIMESTAMP NOT NULL,
    activity_strain                  REAL,
    avg_hr                              REAL,
    max_hr                                 REAL,
    matched_workout_id                       TEXT UNIQUE REFERENCES hevy_workouts(workout_id) ON DELETE SET NULL
);

CREATE TABLE journal_flags (
    journal_flag_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    whoop_daily_id              INTEGER NOT NULL REFERENCES whoop_daily(whoop_daily_id) ON DELETE CASCADE,
    question_text                TEXT NOT NULL,
    answered_yes                    BOOLEAN,
    UNIQUE (whoop_daily_id, question_text)
);