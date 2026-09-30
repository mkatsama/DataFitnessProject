import json
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()  # reads HEVY_API_KEY from the .env file
API_KEY = os.environ["HEVY_API_KEY"]
BASE_URL = "https://api.hevyapp.com/v1/workouts"
HEADERS = {"api-key": API_KEY}
CUTOFF = datetime.now(timezone.utc) - timedelta(days=200)  # past 200 days


def get_recent_workouts(cutoff=CUTOFF):
    all_workouts = []
    page = 1
    page_size = 10  # check your key's max allowed page_size

    while True:
        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        data = response.json()
        workouts = data.get("workouts", [])

        if not workouts:
            break  # no more pages

        for w in workouts:
            workout_date = datetime.fromisoformat(w["start_time"].replace("Z", "+00:00"))
            if workout_date < cutoff:
                return all_workouts  # older than cutoff — stop, since results are newest-first
            all_workouts.append(w)

        page += 1

    return all_workouts



        

TEMPLATES_URL = "https://api.hevyapp.com/v1/exercise_templates"

def get_all_exercise_templates():
    all_templates = []
    page = 1
    page_size = 100  # templates endpoint allows a larger page size

    while True:
        response = requests.get(
            TEMPLATES_URL,
            headers=HEADERS,
            params={"page": page, "page_size": page_size}
        )
        response.raise_for_status()
        data = response.json()
        templates = data.get("exercise_templates", [])

        if not templates:
            break

        all_templates.extend(templates)

        if page >= data.get("page_count", 1):
            break
        page += 1

    return all_templates

if __name__ == "__main__":
    workouts = get_recent_workouts()
    print(f"Fetched {len(workouts)} workouts (since {CUTOFF.date()})")

    templates = get_all_exercise_templates()
    custom = [t for t in templates if t["is_custom"]]
    print(f"Fetched {len(templates)} exercise templates ({len(custom)} custom)")

    out_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(out_dir, "hevy_workouts.json"), "w") as f:
        json.dump(workouts, f, indent=2)

    with open(os.path.join(out_dir, "hevy_exercise_templates.json"), "w") as f:
        json.dump(templates, f, indent=2)

    print("Saved raw data to hevy_workouts.json and hevy_exercise_templates.json")

    if custom:
        print("\nCustom exercises — review these muscle group tags:")
        for t in custom:
            print(f"  {t['title']}: {t['primary_muscle_group']}")