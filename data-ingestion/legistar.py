import os
import json
import time
import requests

from dotenv import load_dotenv

load_dotenv()

LEGISTAR_API_KEY = os.getenv("LEGISTAR_API_KEY")
BASE_URL = "https://webapi.legistar.com/v1/nyc"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "json-data")


def legistar_fetch(endpoint: str, id_field: str, page_size: int = 500):
    url = f"{BASE_URL}/{endpoint}"
    endpoint_slug = endpoint.replace("/", "-")

    records_dir = os.path.join(OUTPUT_DIR, endpoint_slug)
    os.makedirs(records_dir, exist_ok=True)

    checkpoint_path = os.path.join(OUTPUT_DIR, f"{endpoint_slug}.checkpoint.json")

    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
        skip = int(checkpoint.get("next_skip", 0))
        print(f"{endpoint}: resuming from skip={skip}")
    else:
        checkpoint = {}
        skip = 0

    while True:
        fetched = False

        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    params={
                        "token": LEGISTAR_API_KEY,
                        "$top": page_size,
                        "$skip": skip,
                    },
                    timeout=30,
                )
                fetched = True
                break
            except requests.RequestException as exc:
                print(f"{endpoint}: attempt {attempt + 1} failed at skip={skip}: {exc}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if not fetched:
            checkpoint["last_error"] = f"all retries failed at skip={skip}"
            checkpoint["next_skip"] = skip
            _write_checkpoint(checkpoint_path, checkpoint)
            print(f"{endpoint}: giving up at skip={skip}, checkpoint saved")
            return

        if response.status_code != 200:
            checkpoint["last_error"] = f"{response.status_code}: {response.text}"
            checkpoint["next_skip"] = skip
            _write_checkpoint(checkpoint_path, checkpoint)
            print(f"{endpoint}: HTTP {response.status_code} at skip={skip}")
            return

        page = response.json()

        if not page:
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
            print(f"{endpoint}: complete. checkpoint cleared")
            return

        for record in page:
            record_id = record.get(id_field)
            if record_id is None:
                print(f"{endpoint}: missing id field '{id_field}' on record, skipping")
                continue
            record_path = os.path.join(records_dir, f"{record_id}.json")
            with open(record_path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

        skip += len(page)
        checkpoint = {
            "next_skip": skip,
            "page_size": page_size,
            "last_error": None,
        }
        _write_checkpoint(checkpoint_path, checkpoint)
        print(f"{endpoint}: saved {len(page)} records, total skip={skip}")

        if len(page) < page_size:
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
            print(f"{endpoint}: complete. last page had {len(page)} records")
            return

        time.sleep(0.5)


def _write_checkpoint(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

legistar_fetch("events", "EventId")