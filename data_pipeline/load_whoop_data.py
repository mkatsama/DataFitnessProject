import csv 
from datetime import datetime 
import pandas as pd
import sqlite3
import pandas as pd

def load_physiological_cycles(csv_path, conn):
    df = pd.read_csv(csv_path)

    
    df["Cycle start time"] = pd.to_datetime(df["Cycle start time"])
    df["Wake onset"] = pd.to_datetime(df["Wake onset"])

    df["anchor"] = df["Wake onset"].fillna(df["Cycle start time"])
    df["whoop_date"] = df["anchor"].dt.date
    
    df["Cycle end time"] = pd.to_datetime(df["Cycle end time"])
    
    offset_str = df["Cycle timezone"].str.replace("UTC", "", regex=False).str.replace("+", "", regex=False)
    offset_td = pd.to_timedelta(offset_str + ":00")

    df["start_utc"] = df["Cycle start time"] - offset_td
    df["end_utc"] = df["Cycle end time"] - offset_td

    csv_cols = ["whoop_date", "Recovery score %", "Resting heart rate (bpm)",
        "Heart rate variability (ms)", "Day Strain", "Sleep performance %",
        "Respiratory rate (rpm)", "Asleep duration (min)", "Light sleep duration (min)",
        "Deep (SWS) duration (min)", "REM duration (min)", "Awake duration (min)",
        "Sleep need (min)", "Sleep debt (min)", "Sleep efficiency %", "Sleep consistency %",
        "Blood oxygen %", "Skin temp (celsius)", "Energy burned (cal)", "Max HR (bpm)",
        "Average HR (bpm)", "In bed duration (min)"]
    print(df[csv_cols].head(10))

    table_cols = ["whoop_date", "recovery_score", "resting_hr", "hrv_ms", "daily_strain",
        "sleep_performance_pct", "respiratory_rate", "asleep_duration_min", "light_sleep_min",
        "deep_sleep_min", "rem_sleep_min", "awake_min", "sleep_need_min", "sleep_debt_min",
        "sleep_efficiency_pct", "sleep_consistency_pct", "blood_oxygen_pct", "skin_temp_c",
        "energy_burned_cal", "max_hr", "avg_hr", "in_bed_duration_min"]

    prepared = df[csv_cols].copy()  # selecting all the columns from the data frame
    prepared.columns = table_cols
    prepared['whoop_date'] = prepared["whoop_date"].astype(str) # converting date into a string data type
    prepared = prepared.where(pd.notna(prepared), None) # converting NaN into none as the sqlit does not handle NaN


    rows = list(prepared.itertuples(index=False, name = None))

    # Connecting to the database in order to insert the data
    conn.execute("PRAGMA foreign_keys = ON")

    update_cols = table_cols[1:]  # every column except whoop_date, which is the conflict key
    set_clause = ",\n                 ".join(f"{col} = excluded.{col}" for col in update_cols)

    conn.executemany(f"""
                 INSERT INTO whoop_daily ({", ".join(table_cols)})
                 VALUES({",".join(["?"] * len(table_cols))})
                 ON CONFLICT(whoop_date) DO UPDATE SET
                 {set_clause}
                 """, rows)

    conn.commit()

    print(f"inserted/updated {len(rows)} rows into whoop_daily")
    return df


def load_journal_entries(csv_path, conn, cycles_df):
    journal_df = pd.read_csv(csv_path)


    cycle_lookup = cycles_df[["Cycle start time", "whoop_date"]]

    journal_df["Cycle start time"] = pd.to_datetime(journal_df["Cycle start time"])

    journal_df = journal_df.merge(cycle_lookup, on="Cycle start time", how="left")

    print(journal_df.head())
    print(journal_df["whoop_date"].isna().sum(), "rows with no matching cycle")

    journal_df["whoop_date"] = journal_df["whoop_date"].astype(str)

    daily_id_lookup = pd.read_sql("SELECT whoop_date, whoop_daily_id FROM whoop_daily", conn)

    journal_df = journal_df.merge(daily_id_lookup, on="whoop_date", how="left")



    journal_df = journal_df.dropna(subset=["whoop_daily_id"])

    prepared_journal = journal_df[["whoop_daily_id", "Question text", "Answered yes"]].copy()
    prepared_journal.columns = ["whoop_daily_id", "question_text", "answered_yes"]

    prepared_journal["whoop_daily_id"] = prepared_journal["whoop_daily_id"].astype(int)
    prepared_journal = prepared_journal.where(pd.notna(prepared_journal), None)

    journal_rows = list(prepared_journal.itertuples(index=False, name=None))

    conn.executemany("""
    INSERT INTO journal_flags (whoop_daily_id, question_text, answered_yes)
    VALUES (?, ?, ?)
    ON CONFLICT(whoop_daily_id, question_text) DO UPDATE SET
        answered_yes = excluded.answered_yes
    """, journal_rows)

    conn.commit()

    print(f"inserted/updated {len(journal_rows)} rows into journal_flags")
    

def workouts(csv_path, conn):
    
    workouts_df = pd.read_csv("/Users/mariakatsama/Desktop/my_whoop_data_2026_09_21/workouts.csv")
    
    offset_str = workouts_df["Cycle timezone"].str.replace("UTC", "", regex=False)  # "UTC+03:00" -> "+03:00"
    combined = workouts_df["Workout start time"] + offset_str

    
    workouts_df["start_utc"] = pd.to_datetime(combined, utc=True).dt.tz_localize(None)
    
    print(workouts_df[["Activity name", "Workout start time", "Cycle timezone", "start_utc"]].head())

    hevy_lookup = pd.read_sql("SELECT workout_id, start_time_utc FROM hevy_workouts", conn)
    hevy_lookup["start_time_utc"] = pd.to_datetime(hevy_lookup["start_time_utc"], utc=True).dt.tz_localize(None)
    
    workouts_df = workouts_df.sort_values("start_utc")
    hevy_lookup = hevy_lookup.sort_values("start_time_utc")
    
    matched = pd.merge_asof(
        workouts_df, hevy_lookup,
        left_on="start_utc", right_on="start_time_utc",
        direction="nearest", tolerance=pd.Timedelta("20min"),
    )
    
    print(matched[["Activity name", "start_utc", "start_time_utc", "workout_id"]].tail(10))
    print(matched["workout_id"].notna().sum(), "activities matched to a Hevy workout")

    # merge_asof can match two different Whoop activities to the same Hevy workout
    # (e.g. one session logged as two segments). matched_workout_id is UNIQUE, so
    # keep only the closer match per Hevy workout and unmatch the runner-up.
    time_diff = (matched["start_utc"] - matched["start_time_utc"]).abs()
    is_runner_up = matched["workout_id"].notna() & (
        time_diff != time_diff.groupby(matched["workout_id"]).transform("min")
    )
    matched.loc[is_runner_up, "workout_id"] = None
    if is_runner_up.any():
        print(f"unmatched {is_runner_up.sum()} duplicate match(es) (same Hevy workout claimed twice)")

    prepared_activities = matched[["Activity name", "Workout start time", "Workout end time",
                                    "Activity Strain", "Average HR (bpm)", "Max HR (bpm)", "workout_id"]].copy()
    prepared_activities.columns = ["activity_name", "start_time_local", "end_time_local",
                                    "activity_strain", "avg_hr", "max_hr", "matched_workout_id"]
    prepared_activities = prepared_activities.where(pd.notna(prepared_activities), None)

    delete_keys = list(prepared_activities[["activity_name", "start_time_local"]].itertuples(index=False, name=None))
    conn.executemany("DELETE FROM whoop_activities WHERE activity_name = ? AND start_time_local = ?", delete_keys)

    activity_rows = list(prepared_activities.itertuples(index=False, name=None))
    conn.executemany("""
        INSERT INTO whoop_activities (activity_name, start_time_local, end_time_local, activity_strain, avg_hr, max_hr, matched_workout_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, activity_rows)
    conn.commit()
    print(f"inserted/updated {len(activity_rows)} rows into whoop_activities")

def link_hevy_workouts(conn, cycles_df):
    daily_id_lookup = pd.read_sql("SELECT whoop_date, whoop_daily_id FROM whoop_daily", conn)

    cycles_df = cycles_df.copy()
    cycles_df["whoop_date"] = cycles_df["whoop_date"].astype(str)
    cycles_df = cycles_df.merge(daily_id_lookup, on="whoop_date", how="left")
    cycles_df = cycles_df.sort_values("start_utc")

    hevy_df = pd.read_sql("SELECT workout_id, start_time_utc FROM hevy_workouts", conn)
    hevy_df["start_time_utc"] = pd.to_datetime(hevy_df["start_time_utc"], utc=True).dt.tz_localize(None)
    hevy_df = hevy_df.sort_values("start_time_utc")

    matched = pd.merge_asof(
        hevy_df, cycles_df[["start_utc", "end_utc", "whoop_daily_id"]],
        left_on="start_time_utc", right_on="start_utc",
        direction="backward",
    )

    # a workout only belongs to the cycle it matched if it happened before that
    # cycle ended (an open/current cycle has end_utc = NaT -> hasn't ended yet -> always valid)
    inside_window = matched["end_utc"].isna() | (matched["start_time_utc"] < matched["end_utc"])
    matched.loc[~inside_window, "whoop_daily_id"] = None

    update_rows = [
        (None if pd.isna(daily_id) else int(daily_id), workout_id)
        for daily_id, workout_id in zip(matched["whoop_daily_id"], matched["workout_id"])
    ]
    conn.executemany("UPDATE hevy_workouts SET whoop_daily_id = ? WHERE workout_id = ?", update_rows)
    conn.commit()

    linked = sum(1 for daily_id, _ in update_rows if daily_id is not None)
    print(f"linked {linked} hevy_workouts rows to a whoop_daily day")


if __name__ == "__main__":
    conn = sqlite3.connect("/Users/mariakatsama/Desktop/DataFitnessProject/db/fitness_agent.db")
    conn.execute("PRAGMA foreign_keys = ON")

    cycles_df = load_physiological_cycles(
        "/Users/mariakatsama/Desktop/my_whoop_data_2026_09_21/physiological_cycles.csv", conn
    )
    load_journal_entries(
        "/Users/mariakatsama/Desktop/my_whoop_data_2026_09_21/journal_entries.csv", conn, cycles_df
    )
    
    workouts(
            "/Users/mariakatsama/Desktop/my_whoop_data_2026_09_21/workouts.csv", conn
        )

    link_hevy_workouts(conn, cycles_df)

    conn.close()

        