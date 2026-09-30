import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "fitness_agent.db")
WORKOUTS_PATH = os.path.join(BASE_DIR, "hevy_workouts.json")
TEMPLATES_PATH = os.path.join(BASE_DIR, "hevy_exercise_templates.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def upsert_exercises(conn, templates):
    rows = [
        (
            t["id"],
            t["title"],
            t["type"],
            t["primary_muscle_group"],
            t["equipment"],
            t["is_custom"],
            t["primary_muscle_group"] == "quadriceps",
        )
        for t in templates
    ]
    conn.executemany(
        """
        INSERT INTO exercises (
            exercise_template_id, title, exercise_type, primary_muscle_group,
            equipment, is_custom, is_quad_relevant
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exercise_template_id) DO UPDATE SET
            title=excluded.title,
            exercise_type=excluded.exercise_type,
            primary_muscle_group=excluded.primary_muscle_group,
            equipment=excluded.equipment,
            is_custom=excluded.is_custom,
            is_quad_relevant=excluded.is_quad_relevant
        """,
        rows,
    )


def upsert_workouts(conn, workouts):
    rows = [
        (w["id"], w["title"], w["routine_id"], w["start_time"], w["end_time"])
        for w in workouts
    ]
    conn.executemany(
        """
        INSERT INTO hevy_workouts (workout_id, title, routine_id, start_time_utc, end_time_utc)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(workout_id) DO UPDATE SET
            title=excluded.title,
            routine_id=excluded.routine_id,
            start_time_utc=excluded.start_time_utc,
            end_time_utc=excluded.end_time_utc
        """,
        rows,
    )


def replace_workout_sets(conn, workouts):
    workout_ids = [(w["id"],) for w in workouts]
    conn.executemany("DELETE FROM workout_sets WHERE workout_id = ?", workout_ids)

    rows = []
    for w in workouts:
        for exercise in w.get("exercises", []):
            template_id = exercise["exercise_template_id"]
            for s in exercise.get("sets", []):
                rows.append((
                    w["id"],
                    template_id,
                    s["index"],
                    s["type"],
                    s["weight_kg"],
                    s["reps"],
                    s["rpe"],
                ))

    conn.executemany(
        """
        INSERT INTO workout_sets (
            workout_id, exercise_template_id, set_index, set_type, weight_kg, reps, rpe
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def main():
    templates = load_json(TEMPLATES_PATH)
    workouts = load_json(WORKOUTS_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        upsert_exercises(conn, templates)
        upsert_workouts(conn, workouts)
        replace_workout_sets(conn, workouts)
        conn.commit()
    finally:
        conn.close()

    print(f"Loaded {len(templates)} exercises, {len(workouts)} workouts into {DB_PATH}")


if __name__ == "__main__":
    main()
