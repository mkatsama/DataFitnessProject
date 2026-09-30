import sqlite3
from pathlib import Path
import pandas as pd

DB = "db/fitness_agent.db"
OUT = Path("data/exports")
OUT.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DB) as conn, pd.ExcelWriter(OUT / "fitness_data.xlsx") as writer:
    names = pd.read_sql(
        "SELECT name FROM sqlite_master "
        "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'",
        conn,
    )["name"]
    for name in names:
        # Excel caps sheet names at 31 characters
        pd.read_sql(f"SELECT * FROM {name}", conn).to_excel(writer, sheet_name=name[:31], index=False)
        print(f"exported {name}")